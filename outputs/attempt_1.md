# Introduction to RAG

## What you will learn
RAG (Retrieval-Augmented Generation) helps an AI answer using useful information supplied at question time. It is for beginners: think of it as an AI that first looks in a trusted folder, then writes an answer.

## What is RAG?
RAG is a method with two parts: retrieval means finding relevant text; generation means writing a response. The found text is called context. RAG does not magically make every answer true, so the documents and the final answer still need checking.

## Why does it matter?
A normal language model may not know a company's new policy or your school's handbook. RAG can bring that information into the conversation without retraining the whole model. This can make answers more useful and easier to trace back to a document.

## How it works: three steps
1. **Retrieve:** turn the question into a search and find the most relevant passages in a document store (a searchable collection of documents).
2. **Augment:** place those passages, called context, beside the user's question. Augment means “add useful information.”
3. **Generate:** the language model uses the question and context to write an answer. A good system can show the source passages too.

## A simple example
Imagine a school stores its attendance rules in a handbook. A student asks, “How many days can I be absent?” RAG searches the handbook, finds the attendance paragraph, gives that paragraph to the language model, and asks it to answer from that paragraph. If the paragraph does not contain the answer, the system should say it cannot find the answer instead of guessing.

## What RAG cannot do
RAG can retrieve the wrong passage, use an old document, or write an answer that is not supported by the context. It does not remove hallucinations (made-up information). Use trusted, updated documents and check important answers.

## Key words
- **Language model:** software trained to understand and produce text.
- **Retrieval:** finding useful information.
- **Context:** information given to the model for this answer.
- **Hallucination:** an answer that sounds real but is made up or unsupported.

## Quick recap
RAG retrieves relevant information, adds it as context, and then generates an answer. It matters because the model can use changing or private documents. It is helpful, but its sources and answers still need checking.
