import os
from datetime import datetime
from uuid import uuid4

from openai import OpenAI
from uagents import Context, Protocol
from uagents.experimental.chat_agent.protocol import build_llm_message_history
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from http_client import upload_pdf
from pdf_utils import text_to_pdf

SYSTEM_PROMPT = (
    "You are Form Prep Assistant, a careful helper for people filling out forms and applications "
    "(jobs, rentals, government paperwork, school forms, insurance, and similar). "
    "Your three jobs: "
    "1) Explain form questions in plain, simple language; avoid jargon, and if a question is ambiguous, "
    "describe the common interpretations and suggest confirming with the organisation that issued the form. "
    "2) Build practical document checklists: list the documents or information typically needed to answer "
    "the questions the user shares, with a short note on where to find each item. "
      "3) Help the user prepare draft answers: propose clear, honest wording they can review, edit, and paste "
    "into the form themselves. "
    "Hard rules: "
    "- You NEVER submit anything, never claim a form was submitted, and never imply you acted on the user's behalf; "
    "you only prepare explanations, checklists, and drafts. "
    "- Remind the user to review every draft and verify exact requirements with the form provider. "
    "- Do not give definitive legal, tax, medical, or immigration advice; suggest a qualified professional when needed. "
    "- If you are unsure what a question means, say so and ask for the exact wording or surrounding context. "
    "- Always answer in the user's language."
)

PDF_NOTE = (
    " The user asked for a PDF version of your reply: output the complete final document "
    "content as plain text only (no markdown syntax such as **, #, or tables) so it can be "
    "converted directly into a PDF file."
)

client = OpenAI(
    # Agentverse injects both variables into every hosted agent; no key is hardcoded or requested from the user.
    base_url=os.environ["ASI1_BASE_URL"],
    api_key=os.environ["ASI1_API_KEY"],
)

form_protocol = 
Protocol(spec=chat_protocol_spec)


def create_text_chat(text: str) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)


@form_protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    # Acknowledge the incoming message first.
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = msg.text()
    if not text:
        return
      
    # Simple request detection: any message mentioning "pdf" gets a PDF download link.
    wants_pdf = "pdf" in text.lower()

    system_content = SYSTEM_PROMPT + (PDF_NOTE if wants_pdf else "")
    messages = [
        {"role": "system", "content": system_content},
        *build_llm_message_history(ctx),
    ]

    try:
        completion = client.chat.completions.create(
            model="asi1",
            messages=messages,
            max_tokens=2048,
        )
        reply = str(completion.choices[0].message.content or "")
      except Exception:
        ctx.logger.exception("Error querying model")
        reply = (
            "Sorry, something went wrong while preparing an answer. "
            "Please send your question again in a moment."
        )

    if wants_pdf and reply:
        # Convert the document content of this reply into a real PDF file
        # (never Python source code) and try to get a genuine download URL.
        link = None
        try:
            link = upload_pdf(text_to_pdf(reply))
        except Exception:
            ctx.logger.exception("PDF generation or upload failed")
        if link:
            reply = (
                              f"{reply}\n\n---\n"
                "I could not create a working PDF download link this time (the upload to "
                "the file host failed). The full document content is in the text above - "
                "copy it into any document editor and export it as a PDF."
            )

    await ctx.send(sender, create_text_chat(reply))


@form_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass
