import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from control import drive, stop, set_logger

app = FastAPI()
# 정적 파일 (index.html)을 서비스하기 위한 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    # static 폴더 안의 index.html 파일을 반환합니다.
    return FileResponse("static/index.html")

@app.websocket("/ws/joystick")
async def joystick_endpoint(websocket: WebSocket):
    await websocket.accept()

    def send_log(msg: str):
        """GPIO 제어 함수에서 발생한 로그를 클라이언트로 보냄"""
        async def _safe_send():
            try:
                await websocket.send_text(msg)
            except Exception:
                pass
        asyncio.create_task(_safe_send())

    set_logger(send_log) # control.py에 WebSocket 전송 함수 등록

    await websocket.send_text("✅ 사용자 연결됨")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            x = float(payload.get("x", 0))
            y = float(payload.get("y", 0))
           
            # control.py의 drive 함수 호출
            drive(x, y)
           
            print(f"[입력값] x={x:.2f}, y={y:.2f}")
    except WebSocketDisconnect:
        stop()
        print("❌ 사용자 연결 종료")
    finally:
        # 서버 강제 종료 또는 예외 발생 시 모터 정지
        stop()


if __name__ == "__main__":
