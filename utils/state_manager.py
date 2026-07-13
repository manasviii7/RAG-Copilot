import pickle
import os

STATE_PATH = "storage/app_state.pkl"

# ---------------- SAVE STATE ----------------
def save_state(state):

    os.makedirs(
        "storage",
        exist_ok=True
    )

    with open(STATE_PATH, "wb") as f:

        pickle.dump(state, f)

# ---------------- LOAD STATE ----------------
def load_state():

    try:

        if os.path.exists(STATE_PATH):

            with open(STATE_PATH, "rb") as f:

                return pickle.load(f)

    except:
        pass

    return {
        "workspaces": {},
        "current_workspace": None,
        "current_chat": None
    }