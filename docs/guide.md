# Welcome to LETO's user guide

This guide explains how to set up LETO and use its main application UI.

## Setting up

LETO comes packaged with a Docker environment ready to set up.
To get started, you need to either clone the project from Github or obtain the source code via a different channel.
Once you have the source code in place, `cd` into the project root and type:

```bash
make app
```

This command with launch three Docker containers:

- The main LETO application (🔗 <http://localhost:8501>)
- A `neo4j` instance where the backend data is stored (🔗 <http://localhost:7474>)
- A documentation server, like the one hosting these docs right now (🔗 <http://localhost:8000>)

If you're deploying for a production environment, you'll probably want to set up a web server in front of the main application.
In that case, you'd need to either modify `docker/docker-compose.yml` or create a new one (using that file as a starting point) and configure your web server accordingly.

## Overview of the UI

Below is a screenshot of the main LETO application.
We'll guide you through the main components one at a time and how to use them.

![Main UI of the LETO MVP](../img/main-ui.png)

### ⚙️ Basic configuration

The top left panel is titled "⚙️ Config".
In this panel, you can configure the backend connection (either using `neo4j` or a dummy file-based storage driver) and the **query parser**.
If you're using LETO in a language other than English, you will need an appropriate query parser.

For now, LETO ships also with a Spanish parser, which you can select in the "🧙‍♂️ Query parser" combo.

### 🔥 Loading data

LETO runs on data, lots of data. To get data into LETO you'll need to supply one of several possible input types.

The panel titled "🔥 Load new data" will let you select one of several **Loaders** that can introduce data to LETO from different formats.
Currently, these are the options:

- **Synthetic toy examples**: A simple loader that creates a pre-defined small graph which you can use for illustrative purposes.
- **Manually enter tuples**: Allows you to explicitly define new entities and relations.
- **From CSV files**: Reads data from one or more CSV files, automatically inferring entities and relations based on some simple heuristics.
- **From Text File**: Reads natural language from a text file and detects entities and relations using NLP tools.
- **From Plain Text**: Same as the previous one, but you can directly type or paste in the text.
- **From Wikipedia page**: Given a query string for Wikipedia, this loader downloads the corresponding article and runs NLP tools to detect entities and relations.

When you select one specific loader, the UI will change to show its configuration and input. For example, for the file-based loaders you will see a "Browse files" button that allows you to select CSV or text files from your filesystem.

### 🔮 Queying LETO

Once you have data in the system, LETO can start doing its magic.

All the interaction with LETO is through natural language queries. You type a query in main the text input ("🔮 Enter a query...") and LETO will navigate through the information stored, collect the most relevant entities and relations for that query, and present that information in one of several formats.

The most basic output, as shown in the image, is a subset of the knowledge graph that contains the relevant entities and relations.
You will find the most important elements for the query highlighted in different color, e.g., the entities and relations that are explicitly mentioned or those which are very similar.

According to the query and the information available, LETO will try to come up with interesting visualizations.
For example if there's geographical information in the answer, you'll see it on a map.

As an extreme example, a query like "which features predict salary in Data Scientist" will make LETO train a simple machine learning model on the available data and graph the feature importances for you.

![Visualizing feature importances](../img/visualization.png)

### ❓ Example queries

If you've loaded the toy dataset (using the "Synthetic toy examples" loader), you can use one of the pre-defined queries at the right side of LETO's main UI.
These are premade questions that illustrate the types of queries that can be posted to LETO.

## Interacting with the backend

If you want to interact with the backend data, at <http://localhost:7474> you will find neo4j's browser interface.
To connect just enter the username `neo4j` and the password `letoai`.

Neo4j is a graph database that powers all of LETO's queries. Refer to the [official documentation](https://neo4j.com/docs/) for more information on how to use its interface directly.

!!! warning
    Please keep in mind that if you modify the database outside of LETO (i.e., not using one of LETO's loaders), we cannot guarantee the graph will be in a consistent state that LETO can interpret. Tinker with it at your own risk.