from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai

# --- Local Imports ---
from services import graph_service, prompt_service, data_service

# --- Initialization ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY_IRO")) 

# --- FastAPI App ---
app = FastAPI(title="장곡사 미륵불 괘불탱 안내문")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

# --- App Events ---
@app.on_event("startup")
def startup():
    """
    On startup, connect to Neo4j, verify connection, and load essential graph data into app.state.
    This data is fetched only once to improve performance.
    """
    app.state.neo4j_driver = graph_service.get_neo4j_driver()
    try:
        app.state.neo4j_driver.verify_connectivity()
        print("✅ Neo4j 연결 성공")
    except Exception as e:
        print("❌ Neo4j 연결 실패:", e)
        # In a real application, you might want to raise the exception
        # or prevent the app from starting.
        # For this example, we'll let it continue and it will fail on requests.
        return

    graph = graph_service.get_neo4j_graph()
    app.state.graph = graph
    
    # Pre-load all necessary data
    print("Pre-loading graph data...")
    app.state.basic_info = graph_service.get_basic_info(graph)
    app.state.entire_graph_result = graph_service.entire_graph_query(graph)
    app.state.hwagi = graph_service.get_hwagi_entity(graph)
    thesaurus_data = graph_service.get_thesaurus_entity(graph)
    
    # Pre-process data
    app.state.work_summary = data_service.extract_work_summary(app.state.entire_graph_result)
    app.state.converted_thesaurus = [data_service.convert_thesaurus_item(x) for x in thesaurus_data]
    print("✅ Graph data loaded and processed.")


@app.on_event("shutdown")
def shutdown():
    """On shutdown, close the Neo4j driver connection."""
    if hasattr(app.state, 'neo4j_driver'):
        app.state.neo4j_driver.close()
        print("Neo4j connection closed.")

# --- Pydantic Models ---
class GraphQAIn(BaseModel):
    prompt: dict

# --- REST API Endpoints ---
@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/api/graph-cypher-qa")
async def graph_cypher_qa(payload: GraphQAIn, request: Request):
    """
    Generates a descriptive text about the cultural heritage based on user-defined parameters.
    """
    model_name = "gemini-2.5-flash"
    gemini = genai.GenerativeModel(model_name)
    
    try:
        prompt_obj = payload.prompt or {}
        
        engineered_prompt = prompt_service.create_general_prompt(
            prompt_obj,
            basic_info=request.app.state.basic_info,
            converted_thesaurus=request.app.state.converted_thesaurus,
            work_summary=request.app.state.work_summary,
            hwagi=request.app.state.hwagi
        )
        
        response = gemini.generate_content(engineered_prompt)
        
        return {
            "role": prompt_obj.get("role"),
            "depth": prompt_obj.get("depth"),
            "detail": prompt_obj.get("detail"),
            "model": model_name,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/select_prompt")
async def generate_prompt_for_selection(payload: GraphQAIn, request: Request):
    """
    Generates a descriptive text for a specific selected element (icon, item, etc.).
    """
    model_name = "gemini-2.5-flash"
    gemini = genai.GenerativeModel(model_name)

    try:
        prompt_obj = payload.prompt or {}
        label = prompt_obj.get("label")

        if not label:
            raise HTTPException(status_code=400, detail="Label is required.")

        graph = request.app.state.graph
        selected_icon = None
        full_entity_graph = None # For '용화수'

        # Retrieve the specific data based on the label
        if label in ['1', '2', '3', '8', '9']:
            entity_map = {'1': "미륵존불", '2': "노사나불", '3': "비로자나불", '8': "대묘상보살", '9': "법림보살"}
            entity_uri = graph_service.ENTITY_URI_MAP.get(entity_map[label])
            if entity_uri:
                selected_icon = graph_service.entity_graph_query(graph, entity_uri)
        elif label == '용화수':
            selected_icon = graph_service.get_symbol_entity(graph)
            # For '용화수', we also need the data for '미륵존불'
            mirok_uri = graph_service.ENTITY_URI_MAP["미륵존불"]
            full_entity_graph = graph_service.entity_graph_query(graph, mirok_uri)
        elif label == '화기':
            selected_icon = graph_service.get_hwagi_entity(graph)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid label value: {label}")

        if selected_icon is None:
            raise HTTPException(status_code=404, detail=f"Data for label '{label}' not found.")

        # Generate the prompt
        engineered_prompt = prompt_service.create_selection_prompt(
            prompt_obj,
            basic_info=request.app.state.basic_info,
            selected_icon=selected_icon,
            hwagi=request.app.state.hwagi,
            full_entity_graph=full_entity_graph
        )
        
        if not engineered_prompt:
            raise HTTPException(status_code=500, detail="Failed to generate prompt.")

        response = gemini.generate_content(engineered_prompt)

        return {
            "role": prompt_obj.get("role"),
            "depth": prompt_obj.get("depth"),
            "detail": prompt_obj.get("detail"),
            "model": model_name,
            "text": response.text,
        }

    except Exception as e:
        # For debugging, you might want to log the error
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))