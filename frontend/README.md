# Q-CRYPT frontend

This Next.js app provides the interactive research interface. It uses Flask for image preprocessing, configurations A–E, threshold reconstruction, metrics, and experiment results. Large-image runs are classical simulations; no quantum hardware is used for the 128×128 workflow.

From this directory, install dependencies:

```powershell
npm ci
```

Start Flask first from the repository root in one terminal:

```powershell
python app.py
```

Then start the Next.js frontend from this directory in a second terminal:

```powershell
npm run dev
```

The Next.js rewrites proxy API and image requests to the Flask backend at `http://localhost:5000`. Open `http://localhost:5000`; Flask redirects to the frontend at `http://localhost:3000`.

The active encryption/reconstruction API now requires caller-supplied `secret_key_hex` (32 bytes encoded as 64 hex characters). The current browser UI does not yet provide a key-entry flow and does not persist key material; use a direct API client or research API for keyed operations. Do not put the key in localStorage or artifact metadata. See `docs/research/PHASE7_KEY_MODEL.md` for the key and nonce model.

For production validation, run `npm run lint` and `npm run build`. Start the built frontend with `npm run start` while Flask is running.
