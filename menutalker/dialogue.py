from __future__ import annotations

import json
import re
from typing import Any

from .llm import LLMSettings, call_chat_completion, find_meal
from .storage import read_project_text


FINAL_ORDER_MESSAGE = "Thank you for your order. Your meal will be prepared shortly."


def _items(menu: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for category in menu.get("categories", []):
        for item in category.get("items", []):
            result.append({**item, "category_name": category.get("name", "")})
    return result


def initial_message(menu: dict[str, Any]) -> str:
    categories = [category.get("name", "Unnamed") for category in menu.get("categories", [])]
    if not categories:
        return "I could not find menu categories yet. Please upload clearer menu images or try demo mode."
    names = ", ".join(categories[:6])
    return f"I found these categories: {names}. What would you like to hear first?"


def format_meal(meal: str) -> str:
    cleaned = meal.strip()
    if not cleaned:
        return ""

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if len(lines) > 1:
        return "\n".join(lines)

    line = lines[0] if lines else cleaned
    total = ""
    total_match = re.search(r"(.+?)(?:\.\s*)?(Total\s*:\s*.+)$", line, flags=re.IGNORECASE)
    if total_match:
        line = total_match.group(1).strip(" .")
        total = total_match.group(2).strip()

    items = [item.strip(" .") for item in line.split(",") if item.strip(" .")]
    if not items:
        return cleaned

    formatted = []
    for index, item in enumerate(items):
        suffix = "," if index < len(items) - 1 else "."
        formatted.append(f"{item}{suffix}")
    if total:
        formatted.append(total)
    return "\n".join(formatted)


def _mock_response(message: str, state: dict[str, Any]) -> str:
    menu = state["menu"]
    order = state.setdefault("order", [])
    lower = message.lower()
    if any(word in lower for word in ["done", "finish", "no more", "that's all", "不用", "好了", "結束", "沒有"]):
        if not order:
            return "No items have been selected yet. Would you like to hear a few recommendations?"
        total = sum((entry.get("price") or 0) * entry.get("quantity", 1) for entry in order)
        lines = []
        for entry in order:
            price = entry.get("price")
            price_text = f", {price:g}" if isinstance(price, (int, float)) else ""
            lines.append(f"{entry['quantity']} x {entry['name']}{price_text}")
        summary = "; ".join(lines)
        total_text = f" Total: {total:g}." if total else ""
        return f"Here is your final order: {summary}.{total_text}\n<MEAL>{summary}.{total_text}</MEAL>"

    for item in _items(menu):
        name = str(item.get("name", ""))
        if name and (name.lower() in lower or name in message):
            order.append({"name": name, "price": item.get("price"), "quantity": 1})
            return f"Added one {name}. Do you need anything else?"

    categories = menu.get("categories", [])
    for category in categories:
        name = str(category.get("name", ""))
        if name and (name.lower() in lower or name in message):
            items = category.get("items", [])[:4]
            choices = ", ".join(item.get("name", "Unnamed") for item in items)
            return f"In {name}, I can suggest {choices}. Which one would you like?"

    recommended = _items(menu)[:4]
    if recommended:
        choices = ", ".join(item.get("name", "Unnamed") for item in recommended)
        return f"I can suggest {choices}. Which one sounds good?"
    return "I do not see any menu items yet. Please process the menu again."


def respond(message: str, history: list[dict[str, str]], state: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any], str]:
    settings = LLMSettings.from_values(**state.get("llm", {}))
    menu = state.get("menu")
    if not menu:
        history = [*history, {"role": "user", "content": message}, {"role": "assistant", "content": "Please process a menu first."}]
        return history, state, ""

    if settings.provider == "mock":
        answer = _mock_response(message, state)
    else:
        prompt = read_project_text("prompts/prompt_LLM_Conversational_Engine.md")
        system_prompt = f"{prompt}\n\nmenu.json:\n{json.dumps(menu, ensure_ascii=False)}"
        external_history = [
            {"role": entry["role"], "content": entry["content"]}
            for entry in history
            if entry.get("role") in {"user", "assistant"}
        ]
        try:
            answer = call_chat_completion(
                settings,
                system_prompt=system_prompt,
                user_prompt=message,
                history=external_history,
                temperature=0.2,
            )
        except Exception as exc:
            answer = (
                "I could not reach the external LLM for this turn, so I am keeping the current menu loaded. "
                f"Provider error: {exc}\n\n"
                "Please check that the selected Google model name is available for your API key. "
                "For a quick smoke test, try `gemini-flash-latest` and leave Base URL blank."
            )

    meal = find_meal(answer) or ""
    if meal:
        meal = format_meal(meal)
        answer = FINAL_ORDER_MESSAGE

    history = [*history, {"role": "user", "content": message}, {"role": "assistant", "content": answer}]
    state["meal"] = meal or state.get("meal", "")
    return history, state, meal
