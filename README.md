# MenuTalker

MenuTalker is a research prototype for conversational menu understanding and ordering assistance for visually impaired diners. The project converts captured menu pages into a structured menu representation, then uses speech dialogue to help users browse categories, select dishes, confirm options, and prepare an order.

This repository will store the source code, prompts, JSON schemas, sample menu data, and reference files used in the MenuTalker project.

## Research Goal

Printed menus are difficult to access through conventional Optical Character Recognition (OCR)-to-speech workflows because the recognized text is usually read sequentially. MenuTalker instead treats a menu as a semi-structured document. It extracts menu text, combines it with the original menu image, generates a structured JSON menu, and supports concise ordering dialogue similar to interaction with a human server.

## System Overview

The planned MenuTalker workflow is:

1. Capture one or more menu page images.
2. Apply image preprocessing to improve OCR quality.
3. Extract menu text using an OCR engine.
4. Send the OCR text, original menu images, task prompt, and JSON schema to a multimodal Large Language Model (LLM).
5. Generate a structured JSON menu.
6. Use the structured menu for voice-based browsing, item selection, option confirmation, and order summary.

## Prompt Used for Menu Structuring

```text
Using menu_raw_text.txt and menu_image_*.png, infer the menu layout, correct OCR errors, and generate a complete JSON menu conforming to menu.schema.json.
```

## JSON Schema

The current schema for structured menu generation is available at:

- [`menu.schema.json`](./menu.schema.json)

The schema is designed to represent menu categories, optional category-level prices, menu items, item prices, selectable options, and short item descriptions. It is intentionally customizable so that different restaurant types, languages, or menu formats can be supported in later versions.

## Planned Repository Structure

```text
menu-talker/
├── README.md
├── menu.schema.json
├── prompts/
│   └── menu_to_json_prompt.txt
├── samples/
│   ├── images/
│   ├── ocr_text/
│   └── parsed_json/
├── src/
│   ├── capture/
│   ├── ocr/
│   ├── parser/
│   ├── dialogue/
│   └── order_builder/
└── docs/
```

## Planned Modules

| Module | Purpose |
| --- | --- |
| `capture` | Capture menu page images from a camera. |
| `ocr` | Extract text from captured menu images. |
| `parser` | Convert OCR output and menu images into a structured JSON menu. |
| `dialogue` | Conduct concise voice-based ordering interaction. |
| `order_builder` | Store selected items, modifiers, quantities, and total price. |

## Project Status

This repository is currently being prepared for the MenuTalker research paper and prototype implementation. Source code and demonstration files will be added progressively.

## Citation

A formal citation will be added after the related conference paper is accepted or publicly released.
