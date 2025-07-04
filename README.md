# LETO: Learning Engine Through Ontologies

LETO (Learning Engine Through Ontologies) is an innovative, knowledge-driven AI application designed for advanced **knowledge acquisition, integration, and discovery**. Unlike classic document indexing or RAG-based (Retrieval-Augmented Generation) systems, LETO builds a rich, interconnected knowledge base from your diverse data sources, complete with semantic relationships. It then allows you to interact with this knowledge base through a natural, **dialog-based interface**, enabling deep understanding, synthesis of new information, and powerful reporting.

## 🚀 What is LETO?

In today's information-rich world, knowledge workers often drown in vast amounts of data, struggling to find connections, synthesize insights, and make informed decisions. LETO addresses this challenge head-on.

Feed LETO various forms of information—from text files and Word documents to CSVs and websites—and it will transform this disparate data into a coherent, semi-structured knowledge graph. This internal representation combines both a graph structure (showing relationships between entities) and content chunks, allowing for both precise querying and contextual understanding.

### ✨ Key Features

* **Intelligent Data Ingestion:** Supports a wide range of input formats including text files, Word documents, CSVs, and websites.  
* **Semi-Structured Knowledge Graph:** Combines the power of graph databases for relationships with content chunks for contextual understanding.  
* **Semantic Relationship Extraction:** Automatically identifies and links related concepts within your data.  
* **Information Synthesis:** Generates new, inferred knowledge by identifying patterns and connections across your datasets.  
* **Dialog-Based Interface:** Query your knowledge base, generate reports, create graphs, and extract insights through a natural language chat.  
* **Local & Private:** Runs entirely within your own infrastructure, ensuring your data remains private and under your control. No cloud service dependencies.

## 🎯 Who is LETO For?

LETO is designed for **knowledge workers** across various fields who need to work with large amounts of focused knowledge. This includes:

* **Students & Researchers:** Accelerate literature reviews, understand complex topics, and synthesize findings from multiple sources.  
* **Analysts (Business, Data, Financial, etc.):** Uncover trends, connect disparate datasets (e.g., sales reports, customer feedback, contracts) to inform strategic decisions.  
* **Decision Makers:** Quickly grasp the essential insights from vast amounts of organizational data to make informed choices.  
* **Anyone with Large Data Collections:** Organize, explore, and extract value from personal or professional knowledge archives.

## 💡 Use Cases & Examples

* **Academic Research:** A student researching climate change can feed LETO research papers, scientific reports, and news articles, then ask for summaries of key arguments, connections between different studies, or emerging trends.  
* **Business Intelligence:** A business analyst can upload sales data, customer support transcripts, and marketing campaign results to identify customer pain points, successful strategies, and market opportunities.  
* **Legal & Compliance:** Ingest legal documents, contracts, and regulatory guidelines to quickly find relevant clauses, identify obligations, and synthesize information for case preparation.  
* **Personal Knowledge Management:** Create a comprehensive knowledge base from your notes, books, articles, and web clippings, allowing you to recall and connect information across all your personal learning.

## 🛠️ Technologies Used

LETO is built with robust and modern open-source technologies:

* **Python:** The core programming language for the engine.  
* **Milvus:** Utilized for efficient vector similarity search, forming the backbone of the knowledge storage.  
* **Streamlit:** Powers the intuitive, interactive user interface.  
* **ARGO:** For agentic reasoning and orchestration.  
* **Lingo:** For natural language understanding and text processing.  
* **Pumpking:** For robust data ingestion pipelines and transformation.

## 🚀 Getting Started

Getting started with LETO is straightforward:

1. Install:  
   You can install LETO via pip:  
   pip install leto

   Or, if you prefer Docker:  
   docker run \-p 8501:8501 gia-uh/leto  
2. Launch the App:  
   If installed via pip:  
   leto  
   If running via Docker, it's already up. Navigate to http://localhost:8501 (or your chosen port) in your web browser.  
3. **Create a New Domain:** Within the Streamlit application, create a new "domain." A domain is a self-contained database and virtual space for your knowledge graph and content.  
4. Upload Your Data:  
   Start uploading your text files, documents, CSVs, or provide website URLs. LETO will automatically begin building your knowledge graph.  
5. Chat & Explore:  
   Once data is ingested (or even during the process), you can start asking questions about your domain through the dialog interface. You can even manually request the synthesis of new information to be included directly into your graph.

## **⚠️ Project Status**

LETO is currently in **Alpha stage** and is primarily a **research preview**. While functional, it is under active development, and features may evolve. We welcome your feedback\!

## **🤝 Contributing**

We're excited to build LETO with the community\!

* **User Feedback:** Your insights are invaluable\! Please open issues for any **bugs** you encounter or **feature requests** you have.  
* **Code Contributions:** We are happy to accept code contributions, but to ensure alignment with our clear and comprehensive roadmap, **please submit an issue first** to explain your intended contribution.

## 📄 License

LETO is open-source software released under the **AGPL (Affero General Public License)**.

The AGPL is a copyleft license that ensures software freedom. It requires that if you distribute modified versions of LETO, or if you offer LETO as a service over a network, you must make the source code of your modifications available to the users of that service. This promotes transparency and ensures that improvements to the software benefit the entire community. Feel free to use, modify, and distribute it in accordance with the license.
