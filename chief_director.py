import json
def chief_director(state: LabState) -> dict:
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the routing director for a Physical Vapor Deposition (PVD) AI Copilot. "
                        "Your job is to classify the user's query into a route and assign metadata tags.\n\n"

                        "STEP 1: Decide the route ('chat' or 'database').\n"
                        "Differentiate them like this:\n"
                        "- Route to 'chat' ONLY if the message is purely conversational and does not require any scientific, technical, experimental, or literature knowledge.\n"
                        "- Examples of 'chat': 'hello', 'hi', 'how are you', 'thanks', 'okay', 'good morning'.\n"
                        "- Route to 'database' for ANY query involving science, materials, physics, chemistry, engineering, PVD, sputtering, evaporation, thin films, deposition parameters, substrates, targets, plasma, vacuum, crystallinity, morphology, characterization tools, performance, interpretation, or lab methods.\n"
                        "- Examples of 'database': 'What is sputtering yield?', 'How does pressure affect thin film morphology?', 'Explain XRD peak broadening', 'Give papers on TiN coatings', 'Compare SEM and TEM for thin films'.\n"
                        "- If a query mixes small talk with science, science takes priority and you MUST route to 'database'. Example: 'Hi, can you explain how substrate temperature affects grain growth?' -> 'database'.\n"
                        "- If the user asks for papers, notes, authors, mechanisms, comparisons, explanations, process conditions, or interpretation in a scientific context, route to 'database'.\n"
                        "- If you are uncertain, prefer 'database' over 'chat' so technical queries are not dropped.\n\n"

                        "STEP 2: Assign tags.\n"
                        "- If the route is 'chat', the target_tags array MUST be empty [].\n"
                        "- If the route is 'database', read the ENTIRE query and classify it into an array of applicable tags. You MUST ONLY select from these exact four strings:\n"
                        "  1. 'Background': For theory, historical context, fundamental physics, and rationale.\n"
                        "  2. 'Synthesis': For recipes, deposition parameters (temperature, pressure), hardware, and fabrication steps.\n"
                        "  3. 'Characterization': For analytical tools (XRD, SEM, TEM), sample preparation, and physical property observations.\n"
                        "  4. 'Analysis': For performance data, electrochemical impedance (EIS), catalytic activity, and results interpretation.\n\n"

                        "CRITICAL RULES:\n"
                        "- DO NOT invent or hallucinate new tags. Only use the exact strings provided above.\n"
                        "- A query may have multiple tags if multiple intents are present.\n"
                        "- If the database query is too general and doesn't fit a specific category, return an empty array [].\n"
                        "- If the user mentions sample preparation, use 'Characterization'.\n"
                        "- If the user mentions deposition conditions, recipes, hardware, or process steps, use 'Synthesis'.\n"
                        "- If the user mentions results, impedance, performance, or interpretation, use 'Analysis'.\n"
                        "- If the user asks about theory or rationale, use 'Background'.\n\n"

                        'Return strict JSON with EXACTLY this structure: '
                        '{"reasoning": "string", "decision": "chat" | "database", "target_tags": ["Background"] | []}'
                    ),
                },
                {
                    "role": "user",
                    "content": state["original_query"],
                },
            ],
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        return {
            "route": parsed.get("decision", "database"),
            "target_tags": parsed.get("target_tags", []),
        }

    except Exception as error:
        print(f"chief_director error: {error}")
        return {
            "route": "database",
            "target_tags": [],
        }
