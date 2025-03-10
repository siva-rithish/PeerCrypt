import flet as ft
from flet import TextField, ElevatedButton, Text, Row, Column
import asyncio
import websockets
import threading

class Message:
    def __init__(self, user_name: str, text: str, message_type: str):
        self.user_name = user_name
        self.text = text
        self.message_type = message_type

class ChatMessage(Row):
    def __init__(self, message: Message):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls = [
            ft.CircleAvatar(
                content=Text(self.get_initials(message.user_name)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message.user_name),
            ),
            Column(
                [
                    Text(message.user_name, weight="bold"),
                    Text(message.text, selectable=True),
                ],
                tight=True,
                spacing=5,
            ),
        ]

    def get_initials(self, user_name: str):
        return user_name[:1].capitalize() if user_name else "Unknown"

    def get_avatar_color(self, user_name: str):
        colors_lookup = [
            ft.colors.AMBER, ft.colors.BLUE, ft.colors.BROWN, ft.colors.CYAN,
            ft.colors.GREEN, ft.colors.INDIGO, ft.colors.LIME, ft.colors.ORANGE,
            ft.colors.PINK, ft.colors.PURPLE, ft.colors.RED, ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(user_name) % len(colors_lookup)]


async def websocket_client(page: ft.Page, uri, user_name, room_id, chat):
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(f"User {user_name}")
            await websocket.send(f"Join {room_id}")

            async def receive_messages():
                while True:
                    try:
                        message_recv = await websocket.recv()
                        if not message_recv.startswith("<"):
                            message = Message(user_name=user_name, text=f"{message_recv}", message_type="login_message")
                        else:
                            message_proc = message_recv[1:].partition("> ")
                            message = Message(user_name=message_proc[0], text=message_proc[2], message_type="chat_message")
                        on_message(page, message, chat)
                    except websockets.ConnectionClosedOK:
                        print("WebSocket connection closed normally.")
                        break
                    except Exception as e:
                        print(f"Error receiving message: {e}")
                        break

            await receive_messages()
    except Exception as e:
        print(f"WebSocket connection error: {e}")


def on_message(page: ft.Page, message: Message, chat):
    if message.message_type == "chat_message":
        m = ChatMessage(message)
    elif message.message_type == "login_message":
        m = Text(message.text, italic=True, color=ft.colors.BLACK45, size=12)
    chat.controls.append(m)
    page.update()


async def send_message(websocket, message_text, user_name, page, chat):
    try:
        message_to_send = f"<{user_name}> {message_text}"
        await websocket.send(message_to_send)
        page.pubsub.send_all(Message(user_name=user_name, text=message_text, message_type="chat_message"))
    except Exception as e:
        print(f"Error sending message: {e}")


def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.title = "P2Peek"
    page.theme_mode = ft.ThemeMode.LIGHT

    websocket_lock = threading.Lock()
    websocket_container = {"websocket": None}

    chat = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def join_chat_click(e):
        username = join_user_name.value
        room_id = join_room_id.value
        server_url = join_pass_code.value

        if not username or not room_id or not server_url:
            join_user_name.error_text = "Name cannot be blank!" if not username else None
            join_room_id.error_text = "Room ID cannot be blank!" if not room_id else None
            join_pass_code.error_text = "Server URL cannot be blank!" if not server_url else None
            page.update()
        else:
            def start_websocket():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                websocket = new_loop.run_until_complete(websocket_client(page, server_url, username, room_id, chat))
                
                # Store the websocket in a thread-safe way
                with websocket_lock:
                    websocket_container["websocket"] = websocket
                
                new_loop.run_forever()

            websocket_thread = threading.Thread(target=start_websocket)
            websocket_thread.start()

            page.session.set("user_name", username)
            page.dialog.open = False
            new_message.prefix = Text(f"{username}: ")
            page.pubsub.send_all(Message(user_name=username, text=f"{username} has joined the chat.", message_type="login_message"))
            page.update()

    async def send_message_click(e):
        message_text = new_message.value
        username = page.session.get("user_name")

        # Fetch websocket from container in a thread-safe way
        with websocket_lock:
            websocket = websocket_container["websocket"]

        if websocket and message_text:
            await send_message(websocket, message_text, username, page, chat)
            new_message.value = ""
            new_message.focus()
            page.update()

    new_message = TextField(hint_text="Write a message...", autofocus=True, shift_enter=True, min_lines=1, max_lines=5, filled=True, expand=True, on_submit=send_message_click)

    join_user_name = TextField(label="Username", autofocus=True)
    join_room_id = TextField(label="Room Id", password=True)
    join_pass_code = TextField(label="Server URL")

    page.dialog = ft.AlertDialog(
        open=True,
        modal=True,
        title=Text("Welcome!"),
        content=Column([join_user_name, join_room_id, join_pass_code], width=300, height=220, tight=True),
        actions=[ElevatedButton(text="Join chat", on_click=join_chat_click)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.add(
        ft.Container(content=chat, border=ft.border.all(1, ft.colors.OUTLINE), border_radius=5, padding=10, expand=True),
        Row([new_message, ft.IconButton(icon=ft.icons.SEND_ROUNDED, tooltip="Send message", on_click=send_message_click)]),
    )

ft.app(target=main)
