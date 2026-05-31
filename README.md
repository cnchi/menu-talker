# MenuTalker

MenuTalker is a research prototype for conversational menu understanding and ordering assistance for visually impaired diners. The project converts captured menu pages into a structured menu representation, then uses speech dialogue to help users browse categories, select dishes, confirm options, and prepare an order.

This repository stores the JSON schema and Large Language Model (LLM) prompts used in the MenuTalker project. Source code, sample menu data, and demonstration materials will be added progressively.

## Research Goal

Printed menus are difficult to access through conventional Optical Character Recognition (OCR)-to-speech workflows because the recognized text is usually read sequentially. MenuTalker instead treats a menu as a semi-structured document. It extracts menu text, combines it with the original menu image, generates a structured JavaScript Object Notation (JSON) menu, and supports concise ordering dialogue similar to interaction with a human server.

## System Overview

The planned MenuTalker workflow is:

1. Capture one or more menu page images.
2. Apply image preprocessing to improve OCR quality.
3. Extract menu text using an OCR engine.
4. Send the OCR text, original menu images, task prompt, and JSON schema to a multimodal LLM.
5. Generate a structured JSON menu.
6. Use the structured menu for voice-based browsing, item selection, option confirmation, price calculation, and order summary.

## Repository Structure

```text
menu-talker/
├── README.md
├── menu.schema.json
└── prompts/
    ├── prompt_Menu_Structure_Parsing.md
    └── prompt_LLM_Conversational_Engine.md
```

## JSON Schema

The current schema for structured menu generation is available at:

- [`menu.schema.json`](./menu.schema.json)

The schema represents menu categories, optional category-level prices, menu items, item prices, selectable options, and short item descriptions. It is intentionally compact so that different restaurant types, languages, and menu formats can be supported in later versions.

## Prompts

The current prompt files are stored in [`prompts/`](./prompts/):

| File | Purpose |
| --- | --- |
| [`prompt_Menu_Structure_Parsing.md`](./prompts/prompt_Menu_Structure_Parsing.md) | Instructs the LLM to infer menu layout, correct OCR errors, and generate `menu.json` according to `menu.schema.json`. |
| [`prompt_LLM_Conversational_Engine.md`](./prompts/prompt_LLM_Conversational_Engine.md) | Instructs the LLM to conduct one-question-at-a-time ordering dialogue, ask required option and quantity questions, calculate the total price, and return the final order enclosed by `<MEAL>` and `</MEAL>`. |

## Planned Modules

| Module | Purpose |
| --- | --- |
| `capture` | Capture menu page images from a camera. |
| `ocr` | Extract text from captured menu images. |
| `parser` | Convert OCR output and menu images into a structured JSON menu. |
| `dialogue` | Conduct concise voice-based ordering interaction. |
| `order_builder` | Store selected items, modifiers, quantities, and total price. |

## Project Status

This repository is currently being prepared for the MenuTalker research paper and prototype implementation. The schema and prompt files have been added. Source code and demonstration files will be added progressively.

## Citation

A formal citation will be added after the related conference paper is accepted or publicly released.
