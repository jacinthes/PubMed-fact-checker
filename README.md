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
```
docker build -t pubmed-fact-checker
```
```
docker run -p 8501:8501 pubmed-fact-checker
```
## How does it work
### App workflow
