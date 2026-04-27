from dotenv import load_dotenv
load_dotenv()
from rag_chain import extract_memory
from database import init_db, create_session, save_memory, get_memory

init_db()
sid = create_session()

msg = "my name is Yasha"
mem = extract_memory(msg)
print("Extracted memory:", mem)

for k, v in mem.items():
    save_memory(sid, k, v)

saved = get_memory(sid)
print("Saved memory:", saved)