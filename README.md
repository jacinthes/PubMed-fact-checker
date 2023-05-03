# PubMed-fact-checker

The PubMed fact-checker app enables users to verify biomedical claims by comparing them against research papers available on PubMed.

As the number of self-proclaimed experts continues to rise, so does the risk of harmful misinformation. This app showcases the potential of Large Language Models to provide accurate and valuable information to people.

## Try it out!
The app is available at: https://huggingface.co/spaces/jacinthes/PubMed-fact-checker

## Running locally
You can run the app locally using streamlit directly or via Docker. 
In both cases you will need to add your OpenAI API key to secrets.toml file in the .streamlit folder
```
openai_API_key = "your key"
```
### Streamlit - Python and Git needed
```
git clone https://github.com/jacinthes/PubMed-fact-checker.git
```
```
pip install -r requirements.txt
```
```
streamlit run app.py
```
### Docker - Docker needed
Download and save the provided Dockerfile.
```
docker build -t pubmed-fact-checker
```
```
docker run -p 8501:8501 pubmed-fact-checker
```
## How does it work
### App workflow
![Alt text](https://github.com/jacinthes/PubMed-fact-checker/blob/main/app_workflow.png)
### Query rephrasing with GPT3.5
Searching pubmed with unedited natural language does not yield good results. For this reason the user's provided fact is rephrased as a PubMed query. See below example.<br />
Fact: Mediterranean diet helps with weight loss.<br />
Rephrased as query: "Mediterranean diet"[All Fields] AND "weight loss"[All Fields]
### pymed PubMed
Pymed is used to retrieve top 50 relevant articles (article conclusions or abstract) for the given search query. This number can be increased but it leads to longer load times.
### Reranking
PubMed search also returns articles, which are not highly relevant to assess the given fact.
A [cross-encoder](https://www.sbert.net/examples/applications/cross-encoder/README.html) reranker is used, which returns a relevance score for each fact-article pair. Only articles with a positive relevance score are kept and maximum 10. The maximum number is set to limit OpenAI costs.
### Fact-checking
GPT3.5 is prompted to assess whether the given fact is True/False/Undetermined based on the evidence provided in each article. The result of this process is a label for each fact-article pair.
### Results
Articles and labels are then shown to the user using a sunburst chart. Each article is a link, which leads to the pubmed article page.
