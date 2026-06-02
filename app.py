from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import gradio as gr

from menutalker.dialogue import initial_message, respond
from menutalker.image_processing import preprocess_images, save_uploaded_images
from menutalker.llm import LLMSettings
from menutalker.menu_parser import parse_menu
from menutalker.ocr import run_paddle_ocr
from menutalker.storage import new_session_dir


LLM_PROVIDERS = ["mock", "google", "hf", "openai_compatible", "ollama"]


def _default_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    return provider if provider in LLM_PROVIDERS else "mock"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes"}


def process_menu(
    uploaded_files: list[Any],
    provider: str,
    model: str,
    base_url: str,
    api_key: str,
    include_images: bool,
    ocr_lang: str,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[dict[str, Any], str, list[str], str, dict[str, Any], str | None, str | None, list[dict[str, str]], str]:
    if not uploaded_files:
        return {}, "Please upload at least one menu image.", [], "", {}, None, None, [], ""

    session_dir = new_session_dir()
    progress(0.1, desc="Saving uploaded menu pages")
    original_images = save_uploaded_images(uploaded_files, session_dir)

    progress(0.25, desc="Preprocessing images for OCR")
    ocr_images, preview_images = preprocess_images(original_images, session_dir)

    progress(0.45, desc="Running PaddleOCR")
    ocr_result = run_paddle_ocr(ocr_images, session_dir, lang=ocr_lang or "ch")

    settings = LLMSettings.from_values(provider, model, base_url, api_key, include_images)
    progress(0.7, desc="Building structured menu JSON")
    menu, menu_path, parse_warnings = parse_menu(ocr_result.raw_text, original_images, session_dir, settings)

    warnings = [*ocr_result.warnings, *parse_warnings]
    warning_text = ""
    if warnings:
        warning_text = "\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in warnings)

    state = {
        "session_dir": str(session_dir),
        "menu": menu,
        "menu_path": str(menu_path),
        "raw_text_path": str(ocr_result.raw_text_path),
        "llm": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "include_images": include_images,
        },
        "order": [],
        "meal": "",
    }
    greeting = initial_message(menu)
    history = [{"role": "assistant", "content": greeting}]
    status = (
        f"Processed {len(original_images)} page(s). "
        f"OCR engine: {ocr_result.engine_name}. "
        f"LLM provider: {settings.provider}."
        f"{warning_text}"
    )
    return (
        state,
        status,
        [str(path) for path in preview_images],
        ocr_result.raw_text,
        menu,
        str(ocr_result.raw_text_path),
        str(menu_path),
        history,
        "",
    )


def chat(message: str, history: list[dict[str, str]], state: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any], str, str]:
    if not message.strip():
        return history, state, state.get("meal", ""), ""
    history, state, meal = respond(message, history, state or {})
    meal_display = f"<MEAL>\n{meal}\n</MEAL>" if meal else state.get("meal", "")
    return history, state, meal_display, ""


def reset_demo() -> tuple[dict[str, Any], str, list[str], str, dict[str, Any], None, None, list[dict[str, str]], str, str]:
    return {}, "", [], "", {}, None, None, [], "", ""


with gr.Blocks(title="MenuTalker") as demo:
    gr.Markdown(
        "# MenuTalker\n"
        "A conversational menu assistance system for blind diners.\n\n"
        "**Note:** This live demo does not run on the embedded-computer prototype described in the paper, "
        "and it does not use a camera, microphone, or speech output. Instead, it provides a web interface "
        "for testing the same core menu-processing and dialogue modules: menu image preprocessing, OCR, "
        "structured JSON generation, and guided ordering conversation."
    )

    with gr.Accordion("Usage: Expand this section if you are not sure how to use the demo", open=False):
        gr.Markdown(
            "1. Drag and drop one or more menu photo files into the **Menu page images** panel. "
            "You may upload multiple photos when the menu has multiple pages.\n"
            "2. Expand **Runtime settings** and enter the settings for the LLM you want to use:\n"
            "   - **LLM provider:** Choose the provider for your model. For example, select `google` "
            "when using the Google Gemini API. Select `mock` if you do not have an API key; in mock mode, "
            "MenuTalker still runs OCR and produces a simple heuristic demo menu, but the result is not "
            "generated by an external LLM.\n"
            "   - **Model:** Enter the model name you plan to use, such as `gemma-4-26b-a4b-it`.\n"
            "   - **Base URL:** Enter the API base URL for the model provider. For Google, you can use "
            "`https://generativelanguage.googleapis.com/v1beta`.\n"
            "   - **API key:** Enter your API key. For Google models, you can get a key from Google AI Studio.\n"
            "   - **Send menu images to the LLM when the provider supports vision:** Check this option if "
            "your selected model supports image input. This lets the LLM use the menu photos together with "
            "OCR text, which may improve menu understanding.\n"
            "   - **PaddleOCR language:** Choose the language that best matches your menu photos. For example, "
            "choose `japan` for a Japanese menu.\n"
            "3. Click **Process Menu** and wait for the menu to be processed. This may take about two minutes, "
            "depending on OCR and LLM response time.\n"
            "4. When outputs appear on the right side, including the preprocessed image previews, "
            "`menu_raw_text.txt`, and `menu.json`, the menu has been converted into a structured representation "
            "and the ordering assistant is ready.\n"
            "5. Scroll down to **Ordering dialogue** and start chatting in natural language. MenuTalker will ask "
            "questions and help narrow down what you want to order.\n"
            "6. When you finish ordering, the final order will appear in the **Final meal** text box."
        )

    app_state = gr.State({})

    with gr.Row():
        with gr.Column(scale=1):
            uploads = gr.File(
                label="Menu page images",
                file_count="multiple",
                file_types=["image"],
                type="filepath",
            )
            with gr.Accordion("Runtime settings", open=False):
                provider = gr.Dropdown(
                    label="LLM provider",
                    choices=LLM_PROVIDERS,
                    value=_default_provider(),
                    info="Use mock when no external API key is configured.",
                )
                model = gr.Textbox(
                    label="Model",
                    value=os.getenv("LLM_MODEL", ""),
                    placeholder="Example: gemini-flash-latest, gemma-3-27b-it, or llama3.2-vision",
                )
                base_url = gr.Textbox(
                    label="Base URL",
                    value=os.getenv("LLM_BASE_URL", ""),
                    placeholder="Optional. For Google, leave blank or use https://generativelanguage.googleapis.com/v1beta",
                    info="Do not paste an API key here. For Google, a full .../models/<model>:generateContent URL is also accepted.",
                )
                api_key = gr.Textbox(label="API key", type="password", placeholder="Prefer HF Space Secrets for public demos")
                include_images = gr.Checkbox(
                    label="Send menu images to the LLM when the provider supports vision",
                    value=_env_bool("LLM_INCLUDE_IMAGES", False),
                )
                ocr_lang = gr.Dropdown(
                    label="PaddleOCR language",
                    choices=["ch", "en", "japan", "korean", "latin"],
                    value="ch",
                )
            process_btn = gr.Button("Process Menu", variant="primary")
            clear_btn = gr.Button("Reset")

        with gr.Column(scale=2):
            status = gr.Markdown()
            processed_gallery = gr.Gallery(label="Preprocessed image previews", columns=2, height=280)
            raw_text = gr.Textbox(label="menu_raw_text.txt", lines=10)
            menu_json = gr.JSON(label="menu.json")
            with gr.Row():
                raw_file = gr.File(label="Download menu_raw_text.txt")
                menu_file = gr.File(label="Download menu.json")

    gr.Markdown("## Ordering dialogue")
    chatbot = gr.Chatbot(label="MenuTalker", height=420)
    meal_output = gr.Textbox(label="Final meal", lines=5)
    with gr.Row():
        user_message = gr.Textbox(label="Message", placeholder="Ask about the menu or say what you want to order.", scale=5)
        send_btn = gr.Button("Send", variant="primary", scale=1)

    process_btn.click(
        process_menu,
        inputs=[uploads, provider, model, base_url, api_key, include_images, ocr_lang],
        outputs=[app_state, status, processed_gallery, raw_text, menu_json, raw_file, menu_file, chatbot, meal_output],
    )
    send_btn.click(chat, inputs=[user_message, chatbot, app_state], outputs=[chatbot, app_state, meal_output, user_message])
    user_message.submit(chat, inputs=[user_message, chatbot, app_state], outputs=[chatbot, app_state, meal_output, user_message])
    clear_btn.click(
        reset_demo,
        outputs=[app_state, status, processed_gallery, raw_text, menu_json, raw_file, menu_file, chatbot, meal_output, user_message],
    )


if __name__ == "__main__":
    demo.queue().launch(ssr_mode=False)
