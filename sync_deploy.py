import subprocess
import sys

def sync():
    msg = sys.argv[1] if len(sys.argv) > 1 else "auto-sync: update NBA Live Radar"
    print(f"Sincronizzazione automatica con il Cloud in corso: '{msg}'...")
    try:
        subprocess.run(["git", "-C", "c:\\NBA", "add", "."], check=True)
        # Check if there is anything to commit
        res = subprocess.run(["git", "-C", "c:\\NBA", "status", "--porcelain"], capture_output=True, text=True)
        if res.stdout.strip():
            subprocess.run(["git", "-C", "c:\\NBA", "commit", "-m", msg], check=True)
            subprocess.run(["git", "-C", "c:\\NBA", "push", "origin", "main"], check=True)
            print("✅ Sincronizzazione completata! Il cloud si aggiornerà automaticamente tra 20 secondi.")
        else:
            print("Nessuna modifica da sincronizzare. Il cloud è già aggiornato all'ultima versione.")
    except Exception as e:
        print(f"Errore durante la sincronizzazione: {e}")

if __name__ == "__main__":
    sync()
