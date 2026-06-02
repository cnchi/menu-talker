# MenuTalker

[![Hugging Face Space](https://img.shields.io/badge/Hugging%20Face-MenuTalker-FFD21E?logo=huggingface&logoColor=black)](https://cnchi-menutalker.hf.space/)

MenuTalker is a research prototype for conversational menu understanding and ordering assistance for blind diners. Unlike OCR readers that read menu text sequentially, MenuTalker converts menu pages into structured JSON and then guides the diner through a concise ordering dialogue.

Use the Hugging Face Space badge above to try MenuTalker online.

This repository is prepared as a Hugging Face Spaces demo for a GCCE 2026 paper project.

## Paper Resources

If you arrived here from the paper, these are the key files to download or inspect for reproducing the MenuTalker menu parsing and dialogue workflow.

| File | Purpose |
| --- | --- |
| [menu.schema.json](menu.schema.json) | Defines the JSON Schema for the structured `menu.json` output generated from OCR text and menu images. |
| [prompt_Menu_Structure_Parsing.md](prompts/prompt_Menu_Structure_Parsing.md) | Contains the prompt instructions for converting OCR results and menu context into schema-compliant structured menu data. |
| [prompt_LLM_Conversational_Engine.md](prompts/prompt_LLM_Conversational_Engine.md) | Contains the prompt instructions for the conversational ordering engine that guides diners through menu exploration and final order selection. |

## Demo Workflow

The paper describes the intended SBC-based prototype with voice commands, camera capture, OCR, LLM parsing, dialogue, and TTS. The public Hugging Face Space exposes the same core menu-processing and dialogue modules through a Gradio web interface: reviewers upload menu images and interact with the ordering assistant by text.

1. Upload one or more printed-menu page images in the Gradio demo.
2. Save the uploaded pages in a new session directory as `menu_image_01.png`, `menu_image_02.png`, and so on.
3. Preprocess each image with OpenCV and Pillow:
   - correct image orientation and save the page as RGB PNG,
   - optionally enlarge small images with cubic interpolation,
   - convert to grayscale,
   - denoise and lightly blur the image,
   - apply CLAHE contrast enhancement,
   - create an adaptive-threshold binary preview for display in the demo.
4. Run PaddleOCR on the enhanced grayscale images and combine recognized text from all pages into `menu_raw_text.txt`, sorted approximately by page layout.
5. Convert `menu_raw_text.txt`, the original menu images when vision input is enabled, `prompt_Menu_Structure_Parsing.md`, and `menu.schema.json` into a structured `menu.json`.
6. Validate `menu.json` against the JSON Schema and show warnings when validation issues are found. If the external LLM call or JSON extraction fails, the demo falls back to a lightweight OCR-text parser so the workflow remains testable.
7. Use `menu.json` and `prompt_LLM_Conversational_Engine.md` to conduct a concise ordering dialogue instead of reading the whole menu sequentially.
8. End the dialogue when the assistant emits a final order inside `<MEAL>` and `</MEAL>`, matching the ending rule described in the paper.

## LLM Configuration

The paper uses an external multimodal LLM role for menu-structure parsing and conversational ordering. The Hugging Face Space demo keeps this LLM layer configurable instead of loading a large model on free CPU hardware.

Environment variables:

```text
LLM_PROVIDER=mock | google | hf | openai_compatible | ollama
LLM_MODEL=
LLM_BASE_URL=
LLM_API_KEY=
GOOGLE_API_KEY=
GEMINI_API_KEY=
LLM_INCLUDE_IMAGES=false
MENUTALKER_STORAGE_DIR=/data/menutalker
```

Runtime settings in the Gradio UI can override these environment values for a session.

- Use `LLM_PROVIDER=mock` when no external API key is available. PaddleOCR and the UI still run, and MenuTalker generates a heuristic structured menu and mock dialogue from OCR text.
- Use `LLM_PROVIDER=google` for the Google Gemini API or hosted models available to your Google AI Studio API key. The key may be supplied through `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `LLM_API_KEY`, or the UI field.
- For Google, `LLM_MODEL` may be left blank for the demo default (`gemini-flash-latest`). `LLM_BASE_URL` may also be left blank; if set, use `https://generativelanguage.googleapis.com/v1beta`, a `/models` URL, or a full `.../models/<model>:generateContent` endpoint.
- Set `LLM_INCLUDE_IMAGES=true` only when the selected provider and model can accept image input. When enabled, MenuTalker sends the original menu images together with the OCR text for menu-structure parsing.
- Use `LLM_PROVIDER=hf` for Hugging Face Inference Providers through the OpenAI-compatible router. `LLM_MODEL` and an API key are required.
- Use `LLM_PROVIDER=openai_compatible` for any OpenAI-compatible endpoint. `LLM_MODEL`, `LLM_BASE_URL`, and an API key are required.
- Use `LLM_PROVIDER=ollama` for an Ollama-compatible endpoint. If `LLM_BASE_URL` is blank, the code uses `http://localhost:11434/v1`, which is only useful when that endpoint is reachable from the running Space or local environment.

Store API keys in Hugging Face Space Secrets, not in files committed to this repository.

## Storage

Each processed menu runs in its own session directory. The session contains the uploaded page images, processed OCR inputs, binary preview images, `menu_raw_text.txt`, and `menu.json`.

By default, MenuTalker stores session files under the system temporary directory. If you intentionally want generated demo artifacts to persist on a Hugging Face Space with persistent storage, set:

```text
MENUTALKER_STORAGE_DIR=/data/menutalker
```

When a session starts, MenuTalker checks whether the configured storage directory is writable. If it is missing, unset, or not writable, the code automatically falls back to temporary storage.

## Repository Contents

```text
menu-talker/
├── app.py
├── menutalker/
│   ├── dialogue.py
│   ├── image_processing.py
│   ├── llm.py
│   ├── menu_parser.py
│   ├── ocr.py
│   └── storage.py
├── menu.schema.json
├── prompts/
│   ├── prompt_Menu_Structure_Parsing.md
│   └── prompt_LLM_Conversational_Engine.md
├── requirements.txt
└── README.md
```

## License

Apache License 2.0.
