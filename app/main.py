"""FastAPI: POST /advise + 정적 프론트 서빙(같은 origin)."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.decide import decide, InvalidState

app = FastAPI(title="Poker Advisor")


class GameState(BaseModel):
    hole: list[str]
    board: list[str] = []
    numOpponents: int
    pot: float
    toCall: float
    myStack: float


@app.post("/advise")
def advise(state: GameState):
    try:
        return decide(state.model_dump())
    except InvalidState as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# 정적 프론트 서빙. check_dir=False → static/이 아직 없어도 import 가능(프론트는 Task 5).
app.mount("/", StaticFiles(directory="static", html=True, check_dir=False), name="static")
