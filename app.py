import streamlit as st
import GPTHelper
from sentence_transformers import CrossEncoder
from pymed import PubMed
import pandas as pd
import plotly.express as px
import logging
from langdetect import detect
from typing import Dict, List


if 'valid_inputs_received' not in st.session_state:
    st.session_state['valid_inputs_received'] = False


def get_articles(query, fetcher) -> Dict[List[str], List[str]]:
    # Fetches articles using pymed. Increasing max_results results in longer loading times.
    results = fetcher.query(query, max_results=50)
    conclusions = []
    titles = []
    links = []
    for article in results:
        article_id = 0  # If PubMed search fails to return anything
        try:
            article_id = article.pubmed_id[:8]  # Sometimes pymed wrongly returns a long list of ids. Use only the first
            # [] can cause the cross-encoder to misinterpret string as a list
            title = article.title.replace('[', '(').replace(']', ')')
            conclusion = article.conclusions
            abstract = article.abstract
            article_url = f'https://pubmed.ncbi.nlm.nih.gov/{article_id}/'
            article_link = f'<a href="{article_url}" style="color: black; font-size: 16px; ' \
                           f'text-decoration: underline;">PubMed ID: {article_id}</a>'  # Injects a link to plotly
            if conclusion:
                # Not all articles come with the provided conclusions. Abstract is used alternatively.
                conclusion = conclusion.replace('[', '(').replace(']', ')')
                conclusions.append(title+'\n'+conclusion)
                titles.append(title)  # Title is added to the conclusion to improve relevance ranking.
                links.append(article_link)
            elif abstract:
                abstract = abstract.replace('[', '(').replace(']', ')')
                conclusions.append(title + '\n' + abstract)
                titles.append(title)
                links.append(article_link)
        except Exception as e:
            logging.warning(f'Error reading article: {article_id}: ', exc_info=e)

    return {
        'Conclusions': conclusions,
        'Links': links
    }


@st.cache_resource
def load_cross_encoder():
    # The pretrained cross-encoder model used for reranking. Can be substituted with a different one.
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return cross_encoder


@st.cache_resource
def load_pubmed_fetcher():
    pubmed = PubMed(tool='PubmedFactChecker', email='stihec.jan@gmail.com')
    return pubmed


def run_ui():
    # This function controls the whole app flow.
    st.set_page_config(page_title='PUBMED FACT-CHECKER', page_icon='📖')

    sidebar = st.sidebar
    sidebar.title('ABOUT')
    sidebar.write('''
                The PubMed fact-checker app enables users to verify biomedical claims by comparing them against 
                research papers available on PubMed. \n
                As the number of self-proclaimed experts continues to rise, 
                so does the risk of harmful misinformation. This app showcases the potential of Large Language Models 
                to provide accurate and valuable information to people.
            ''')
    sidebar.title('EXAMPLES')
    sidebar.write('Try one of the below examples to see PubMed fact-checker in action.')

    st.title('PubMed FACT CHECKER')
    with st.form(key='fact_form'):
        fact = st.text_input('Fact:', placeholder='Enter your fact', key='form_input')
        submitted = st.form_submit_button('Fact-Check')

    if sidebar.button('Mediterranean diet helps with weight loss.', use_container_width=250):
        submitted = True
        fact = 'Mediterranean diet helps with weight loss.'

    if sidebar.button('Low Carb High Fat diet is healthy in long term.', use_container_width=250):
        submitted = True
        fact = 'Low Carb High Fat diet is healthy in long term.'

    if sidebar.button('Vaccines are a cause of autism.', use_container_width=250):
        submitted = True
        fact = 'Vaccines are a cause of autism.'
    
    sidebar.title('HOW IT WORKS')
    sidebar.write('Source code and an in-depth app description available at:')
    sidebar.info('**GitHub: [@jacinthes](https://github.com/jacinthes/slovene-nli-benchmark)**', icon="💻")
    sidebar.title('DISCLAIMER')
    sidebar.write('This project is meant for educational and research purposes. \n'
                  'PubMed fact-checker may provide inaccurate information.')

    if not submitted and not st.session_state.valid_inputs_received:
        st.stop()

    elif submitted and not fact:
        st.warning('Please enter your fact before fact-checking.')
        st.session_state.valid_inputs_received = False
        st.stop()

    elif submitted and not detect(fact) == 'en':
        st.warning('Please enter valid text in English. For short inputs, language detection is sometimes inaccurate.'
                   ' Try making the fact more verbose.')
        st.session_state.valid_inputs_received = False
        st.stop()

    elif submitted and not len(fact) < 75:
        st.warning('To ensure accurate searching, please keep your fact under 75 characters.')
        st.session_state.valid_inputs_received = False
        st.stop()

    elif submitted or st.session_state.valid_inputs_received:
        pubmed_query = GPTHelper.gpt35_rephrase(fact)  # Call gpt3.5 to rephrase the fact as a PubMed query.
        pubmed = load_pubmed_fetcher()

        with st.spinner('Fetching articles...'):
            articles = get_articles(pubmed_query, pubmed)

        article_conclusions = articles['Conclusions']
        article_links = articles['Links']
        if len(article_conclusions) == 0:
            # If nothing is returned by pymed, inform user.
            st.info(
                "Unfortunately, I couldn't find anything for your search.\n"
                "Don't let that discourage you, I have over 35 million citations in my database.\n"
                "I am sure your next search will be more successful."
            )
            st.stop()

        cross_inp = [[fact, conclusions] for conclusions in article_conclusions]

        with st.spinner('Assessing article relevancy...'):
            cross_encoder = load_cross_encoder()
            cross_scores = cross_encoder.predict(cross_inp)  # Calculate relevancy using the defined cross-encoder.

        df = pd.DataFrame({
            'Link': article_links,
            'Conclusion': article_conclusions,
            'Score': cross_scores
        })
        df.sort_values(by=['Score'], ascending=False, inplace=True)
        df = df[df['Score'] > 0]  # Only keep articles with relevancy score above 0.
        if df.shape[0] == 0:  # If no relevant article is found, inform the user.
            st.info(
                "Unfortunately, I couldn't find anything for your search.\n"
                "Don't let that discourage you, I have over 35 million citations in my database.\n"
                "I am sure your next search will be more successful."
            )
            st.stop()

        df = df.head(10)  # Keep only 10 most relevant articles. This is done to control OpenAI costs and load time.
        progress_text = 'Assessing the validity of the fact based on relevant research papers.'
        fact_checking_bar = st.progress(0, text=progress_text)
        step = 100/df.shape[0]
        percent_complete = 0
        predictions = []
        for index, row in df.iterrows():
            prediction = GPTHelper.gpt35_check_fact(row['Conclusion'], fact)  # Prompt to GPT3.5 to fact-check
            # For output purposes I use True, False and Undetermined as labels.
            if prediction == 'Entails':
                predictions.append('True')
            elif prediction == 'Contradicts':
                predictions.append('False')
            elif prediction == 'Undetermined':
                predictions.append(prediction)
            else:
                # If GPT3.5 returns an invalid response. Has not happened during testing.
                predictions.append('Invalid')
                logging.warning(f'Unexpected prediction: {prediction}')

            percent_complete += step/100
            fact_checking_bar.progress(round(percent_complete, 2), text=progress_text)
        fact_checking_bar.empty()
        df['Prediction'] = predictions
        df = df[df.Prediction != 'Invalid']  # Drop rows with invalid prediction.
        # Prepare DataFrame for plotly sunburst chart.
        totals = df.groupby('Prediction').size().to_dict()
        df['Total'] = df['Prediction'].map(totals)

        fig = px.sunburst(df, path=['Prediction', 'Link'], values='Total', height=600, width=600, color='Prediction',
                          color_discrete_map={
                                'False': "#FF8384",
                                'True': "#A5D46A",
                                'Undetermined': "#FFDF80"
                            }
                          )
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            font_size=32,
            font_color='#000000'
        )
        st.write(f'According to PubMed "{fact}" is:')
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    run_ui()
