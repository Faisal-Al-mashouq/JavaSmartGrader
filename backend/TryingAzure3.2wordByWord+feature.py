from dotenv import load_dotenv
import os
import cv2
import numpy as np
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient, AnalysisFeature
from google import genai

load_dotenv()
GEMINI_KEY = os.getenv("API_GEMINI")
AZURE_ENDPOINT = "https://gpfirsttrydoc.cognitiveservices.azure.com/"
AZURE_KEY = os.getenv("API_AZURE")

def get_azure_word_map(image_path):
    print(f" Analyzing {image_path} with Azure High-Res Layout...")
    client = DocumentAnalysisClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))

    with open(image_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            document=f,
            features=[AnalysisFeature.OCR_HIGH_RESOLUTION],
        )
    result = poller.result()

    # we will build a list of lines, where each line is a string containing word tags
    detailed_lines = []

    for page in result.pages:
        for line in page.lines:
            # We reconstruct the line word-by-word with confidence
            # this will Find words that belong to this line based on spans
            line_start = line.spans[0].offset
            line_end = line_start + line.spans[0].length

            line_words = [
                w for w in page.words if w.span.offset >= line_start and (w.span.offset + w.span.length) <= line_end
            ]

            # Create the "Annotated String"
            # Example: public[99] static[98] void[95]
            annotated_line = ""
            for word in line_words:
                # content = word text, confidence = 0.0 to 1.0
                conf_int = int(word.confidence * 100)
                annotated_line += f"{word.content}[{conf_int}] "

            detailed_lines.append(annotated_line.strip())
            print(f"Captured: {annotated_line}")  # this will show the ocr result before going to LLm model

    return detailed_lines


def fix_with_gemini_word_level(annotated_lines):
    print("\n Sending Word-Level Data to Gemini...")
    client = genai.Client(api_key=GEMINI_KEY)

    # PROMPT: Teach Gemini how to read the [score] tags, the prompt needs more work
    system_instruction = """
    ROLE: You are a strict OCR Post-Processing Engine. You are NOT a coding tutor.
    INPUT: Java code where every word has a confidence score (e.g., public[99], vold[45]).

    YOUR PRIME DIRECTIVE:
    Preserve the student's logic exactly as written, even if it is wrong.

    --- RULES OF ENGAGEMENT ---

    1. FIX OCR NOISE (High Certainty of Machine Error):
        - '1' looking like 'l' or 'I' (e.g., 'System.out.print1n' -> 'println')
        - '0' looking like 'o' inside numbers (e.g., 'int x = 1o;' -> '10')
        - Missing semicolons at the end of lines IF the confidence of the last word was low.
        - Typos in standard keywords (e.g., 'publIc' -> 'public', 'viod' -> 'void').

    2. DO NOT FIX STUDENT LOGIC (High Certainty of Human Error):
        - Infinite loops (e.g., 'for(int i=0; i>10; i++)'). KEEP IT.
        - Assignment instead of equality (e.g., 'if (x = 5)'). KEEP IT.
        - Logic bugs (e.g., 'System.out.print(x)' where 'x' is undefined). KEEP IT.
        - Wrong variable names (e.g., 'String argss'). KEEP IT.

    3. USE CONFIDENCE SCORES:
        - If a word is 'while[99]' but the syntax is wrong, TRUST THE SCORE. The student wrote it wrong.
        - If a word is 'wh1le[40]', FIX IT. It's an OCR error.

    OUTPUT:
    Return ONLY the raw Java code. Do not add markdown like ```java. Do not add comments explaining your fixes.
    """

    prompt = f"{system_instruction}\n\n### RAW INPUT:\n"
    for line in annotated_lines:
        prompt += f"{line}\n"

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",  # this the model used for fixing OCR missreads
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"


if __name__ == "__main__":
    annotated_data = get_azure_word_map("page_105.png")  # this method requires the image path

    if annotated_data:
        fixed_code = fix_with_gemini_word_level(annotated_data)

        print("\n" + "=" * 40)
        print("      FINAL RESTORED CODE      ")
        print("=" * 40)
        print(fixed_code)
