---
title: MenuTalker
emoji: 🍽️
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.15.2
app_file: app.py
python_version: "3.11"
license: apache-2.0
short_description: A conversational menu assistance system for blind diners.
suggested_hardware: cpu-basic
suggested_storage: small
tags:
  - accessibility
  - ocr
  - gradio
  - menu-understanding
  - assistive-technology
---

# MenuTalker

MenuTalker is a research prototype for conversational menu understanding and ordering assistance for blind diners. Unlike OCR readers that read menu text sequentially, MenuTalker converts menu pages into structured JSON and then guides the diner through a concise ordering dialogue.

This repository is prepared as a Hugging Face Spaces demo for a GCCE 2026 paper project.

## Demo Workflow

1. Upload one or more restaurant menu page images.
2. Save the pages as `menu_image_01.png`, `menu_image_02.png`, and so on in a temporary session workspace.
3. Preprocess each image with OpenCV:
   - resize with cubic interpolation,
   - convert to grayscale,
   - denoise lightly,
   - apply CLAHE contrast enhancement,
   - create an adaptive-threshold preview image.
4. Run PaddleOCR and combine all recognized text into `menu_raw_text.txt`.
5. Convert OCR text, menu images, prompt instructions, and `menu.schema.json` into `menu.json`.
6. Use `menu.json` to conduct a ChatGPT-style ordering dialogue.
7. End the dialogue when the assistant emits a final order inside `<MEAL>` and `</MEAL>`.

## LLM Configuration

The demo intentionally does not load a large LLM on free Hugging Face Space CPU hardware. Instead, the LLM layer is configurable.

Environment variables:

```text
LLM_PROVIDER=mock | hf | openai_compatible | ollama
LLM_MODEL=
LLM_BASE_URL=
LLM_API_KEY=
LLM_INCLUDE_IMAGES=false
MENUTALKER_STORAGE_DIR=/data/menutalker
```

Recommended public-demo setup:

- Use `LLM_PROVIDER=mock` when no external API key is available. The OCR and UI still run, and MenuTalker produces a heuristic demo menu.
- Use `LLM_PROVIDER=hf` for Hugging Face Inference Providers through the OpenAI-compatible router.
- Use `LLM_PROVIDER=openai_compatible` for any OpenAI-compatible endpoint.
- Use `LLM_PROVIDER=ollama` only when the Space can reach a deployed Ollama-compatible endpoint. A local Ollama server on your own computer is not reachable from a public Space unless you expose it deliberately.

Store API keys in Hugging Face Space Secrets, not in files committed to this repository.

## Storage

The Space has a storage bucket mounted at `/data`. For privacy, MenuTalker uses the system temporary directory by default. If you intentionally want uploaded images, OCR text, and generated JSON to persist in the mounted bucket, set:

```text
MENUTALKER_STORAGE_DIR=/data/menutalker
```

If this variable is not set, MenuTalker writes session files to temporary storage instead.

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

The local `references/` folder contains paper drafts and design notes. It is intentionally ignored by both Git and Hugging Face upload rules.

## License

Apache License 2.0.
