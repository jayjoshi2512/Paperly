# Enterprise 3-Level Conversational Memory Architecture

To move beyond simply passing the last 5 messages, an enterprise-grade RAG application requires a tiered memory architecture. This ensures the AI can handle immediate context, recall past topics semantically, and maintain a high-level understanding of the user's goals without blowing up the context window.

Below is the proposed 3-Level Memory Architecture for Paperly:

## Level 1: Short-Term Buffer Memory (Recency)
**Purpose:** Maintain the immediate conversational flow and handle direct follow-up pronouns (e.g., "What does *it* mean?").
*   **Mechanism:** Keep a strict sliding window of only the last **2 to 3 turns** (4-6 messages).
*   **Execution:** Passed directly into the LLM context window.
*   **Advantage:** Extremely fast, highly relevant to the immediate query, and costs very few tokens.

## Level 2: Semantic Vector Memory (Mid-Term)
**Purpose:** Recall relevant facts or context from earlier in the conversation (or past conversations) that have fallen out of the Level 1 buffer.
*   **Mechanism:** Every time a query and answer are generated, they are concatenated and embedded into a vector space (e.g., stored in Qdrant in a `chat_history` collection).
*   **Execution:** When a new query is received, we run a semantic vector search against the user's past chat history. The top 2-3 most semantically similar past exchanges are retrieved and injected into the prompt as "Recalled Past Context".
*   **Advantage:** Allows the user to say "Go back to what we discussed earlier about the Q3 report" even if that conversation was 50 messages ago.

## Level 3: Entity & Topic Summarization (Long-Term)
**Purpose:** Maintain a continuous, high-level understanding of the user's overarching goals, extracted entities, and preferences throughout the session.
*   **Mechanism:** A background LLM task asynchronously monitors the chat. Every ~5 turns, it updates a "Session Summary State" (stored in the relational database). This state contains key extracted entities (e.g., *Current Focus: Acme Corp Financials 2023*, *User Preference: Bullet points*).
*   **Execution:** This short paragraph of synthesized state is constantly injected into the `system` prompt.
*   **Advantage:** The AI never loses track of the "big picture", preventing it from becoming hyper-focused only on recent messages or isolated semantic chunks.

---

### Execution Pipeline Flow

When a user submits a query `Q`:

1. **State Injection (Level 3):** Fetch the current "Session Summary" from SQL.
2. **Semantic Recall (Level 2):** Embed `Q` -> Search Qdrant `chat_history` -> Retrieve Top 2 past exchanges.
3. **Query Condensation:** Combine `Q` with the Level 1 buffer (last 2 messages) to rewrite `Q` into a standalone query `Q'`.
4. **Knowledge Retrieval:** Run `hybrid_search` on the actual document chunks using `Q'`.
5. **Final Generation:** Pass the System Prompt (with Level 3 summary), Level 2 recalled context, Level 1 buffer, retrieved document chunks, and `Q` into the Generator LLM.
6. **Async Cleanup:** Save the new Q&A to SQL, embed it to Qdrant (Level 2), and optionally trigger a summary update (Level 3).
