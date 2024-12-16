# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "pandas",
#   "numpy",
#   "matplotlib",
#   "seaborn",
#   "chardet",
#   "scikit-learn",
#   "tabulate",
# ]
# ///




import os
import sys
import json
import chardet
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split



def detect_encoding(file_path):
    """
    Detect the encoding of the given file.
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding']

# Load dataset with detected encoding...
def load_dataset(file_path):
    try:
        encoding = detect_encoding(file_path)
        print(f"Detected encoding for {file_path}: {encoding}")
        fl = pd.read_csv(file_path, encoding=encoding)
        print(f"Successfully loaded dataset: {file_path}")
        return fl
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def analyze_dataset(data):
    """Analyzes the dataset and generates statistical summaries, visualizations, and clustering."""
    try:

        # Basic summary
        description = data.describe(include='all').transpose()
        missing_values = data.isnull().sum()

        # Data types and unique values
        column_info = {
            col: {
                "type": str(data[col].dtype),
                "unique_values": data[col].nunique()
            } for col in data.columns
        }

        # Correlation matrix for numeric data
        numeric_data = data.select_dtypes(include=['float64', 'int64'])
        correlation_matrix = numeric_data.corr()

       
        if not correlation_matrix.empty:
            plt.figure(figsize=(12.4, 6.4))
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f')
            plt.title('Correlation Matrix')
            plt.savefig('correlation_matrix.png', dpi=100)
            plt.close()
           

        # Clustering analysis (if enough numeric features)
        if numeric_data.shape[1] >= 2:
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_data.dropna())

            kmeans = KMeans(n_clusters=3, random_state=42)
            clusters = kmeans.fit_predict(scaled_data)
            data = data.loc[numeric_data.dropna().index]  # Align with valid indices
            data['Cluster'] = clusters

            
            plt.figure(figsize=(8.4, 6.4))
            sns.scatterplot(x=scaled_data[:, 0], y=scaled_data[:, 1], hue=clusters, palette='viridis')
            plt.title('Cluster Visualization (First Two Features)')
            plt.savefig('cluster_visualization.png', dpi=100)
            plt.close()
               

        # Outlier detection
        iso_forest = IsolationForest(random_state=42, contamination=0.05)
        outliers = iso_forest.fit_predict(numeric_data.dropna())
        data['Outlier'] = outliers

        
        plt.figure(figsize=(8.4, 6.4))
        sns.scatterplot(x=scaled_data[:, 0], y=scaled_data[:, 1], hue=outliers, palette='coolwarm')
        plt.title('Outlier Detection')
        plt.savefig('outlier_visualization.png', dpi=100)
        plt.close()
    

        # Regression analysis
        regression_results = {}
        for target_col in numeric_data.columns:
            other_cols = [col for col in numeric_data.columns if col != target_col]
            if other_cols:
                X = numeric_data[other_cols].dropna()
                y = numeric_data[target_col].dropna()
                common_indices = X.index.intersection(y.index)
                X, y = X.loc[common_indices], y.loc[common_indices]

                if len(X) > 1:
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                    model = LinearRegression()
                    model.fit(X_train, y_train)
                    score = model.score(X_test, y_test)
                    regression_results[target_col] = {
                        "score": score,
                        "coefficients": dict(zip(other_cols, model.coef_)),
                        "intercept": model.intercept_
                    }

                

        return {
            "description": description.to_dict(),
            "missing_values": missing_values.to_dict(),
            "column_info": column_info,
            "correlation_matrix": correlation_matrix.to_dict() if not correlation_matrix.empty else None,
            "clusters": clusters.tolist() if numeric_data.shape[1] >= 2 else None,
            "regression_results": regression_results
        }

    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)

def generate_story(analysis, dataset_name):
    """Generates an engaging story based on the analysis results."""
    prompt = f"""
    Analyze this dataset and narrate findings interactively. Here is the data:

    - Dataset Name: {dataset_name}
    - Columns and Types: {json.dumps(analysis['column_info'], indent=2)}
    - Summary Statistics: {json.dumps(analysis['description'], indent=2)}
    - Missing Values: {json.dumps(analysis['missing_values'], indent=2)}
    - Correlation Matrix: {json.dumps(analysis['correlation_matrix'], indent=2) if analysis['correlation_matrix'] else 'Not Available'}
    - Clusters: {analysis['clusters'][:5]} (truncated) if analysis['clusters'] else 'Not Available'
    - Regression Results: {json.dumps(analysis['regression_results'], indent=2)}

    Create a conversational and engaging story about this data. Include:
    
    "Using the above data summary, statistics, and visualizations, write a comprehensive analysis story. "
    "Include insights derived from the data, trends observed in visualizations, and their implications. "
    "Focus on providing actionable recommendations based on the findings. "
    "Make the story detailed and engaging for a technical audience."

    Keep the narrative concise yet complete, as if explaining to a curious peer.
    """
    return query_llm(prompt)



def query_llm(prompt):
    """
    Queries the LLM for insights and returns the response.
    """
    try:
        url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {AIPROXY_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",  # Supported chat model
            "messages": [
                {"role": "system", "content": "You are a helpful data analysis assistant. Provide insights, suggestions, and implications based on the given analysis and visualizations."},
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Automatically raises HTTP errors if any
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error querying AI Proxy: {e}")
        return "Error: Unable to generate narrative."



def save_story_to_markdown(story, analysis, dataset_name):
    """Saves the story and analysis summary to a markdown file."""
    with open(f'{dataset_name}_README.md', 'w') as f:
        f.write(f"# Analysis of {dataset_name}\n\n")
        f.write("## Summary\n")
        f.write(story + "\n\n")

def main():
    """Main function to analyze the dataset and generate a report."""
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
     
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    dataset_name = os.path.splitext(os.path.basename(file_path))[0]
    print(f"\nAnalyzing file: {file_path}")
    fl = load_dataset(file_path)
    if fl is None:
        sys.exit(1)


    print("Analyzing dataset...")
    analysis = analyze_dataset(fl)

    print("Generating story...")
    story = generate_story(analysis, dataset_name)

    print("Saving outputs...")
    save_story_to_markdown(story, analysis, dataset_name)
    print(f"Analysis complete. Results saved in {dataset_name}_README.md and visualization files.")


AIPROXY_TOKEN = os.environ["AIPROXY_TOKEN"]
if not AIPROXY_TOKEN :
  raise EnvironmentError("AIPROXY_TOKEN is not set. Please set it before running the script.")



if __name__ == "__main__":
    main()
