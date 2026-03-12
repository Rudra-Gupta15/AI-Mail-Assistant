from langchain.prompts import PromptTemplate

EMAIL_RESPONSE_PROMPT = PromptTemplate(
    input_variables=["sender", "subject", "body", "context"],
    template="""You are a professional email assistant.

From: {sender}
Subject: {subject}
Context: {context}

Message:
{body}

Write a professional, helpful response (2-4 sentences):"""
)

CLASSIFICATION_PROMPT = """Analyze this email. Reply with ONE WORD ONLY:

AUTO - for: simple questions, greetings, FAQ
HUMAN - for: complaints, urgent issues, complex problems

Subject: {subject}
Body: {body}

Decision:"""