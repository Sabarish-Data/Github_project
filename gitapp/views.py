import re
import base64
import requests
import openai
from github import Github
from django.http import JsonResponse
from django.shortcuts import render
from django.http import HttpResponseServerError
from decouple import config
openai.api_key = config('OPENAI_API_KEY')
github_token=config('GITHUB_TOKEN')
def extract_username_from_url(url):
    # Regular expression pattern to extract the username from the URL
    pattern = r"github.com/([^/]+)"

    # Find the match using regular expression
    match = re.search(pattern, url)

    if match:
        username = match.group(1)
        return username
    else:
        return None

def retrieve_user_repositories(username, extensions, langchain=None):
    try:
        # Authenticate using your personal access token
        g =Github(github_token)

        # Retrieve the user
        user = g.get_user(username)

        # Retrieve the repositories of the user
        repositories = user.get_repos()

        # Create a list to store the repository data
        repository_data = []

        # Process or display the repository data as needed
        for repo in repositories:
            try:
                # Retrieve the contents of each file in the repository
                contents = repo.get_contents("")
                code_size = 0
                for content in contents:
                    if content.type == "file" and any(content.name.endswith(ext) for ext in extensions):
                        try:
                            file_content = base64.b64decode(content.content).decode("utf-8")
                            code_size += len(file_content)
                        except UnicodeDecodeError:
                            print(f"Failed to decode content for file: {content.name}")

                if code_size > 0:
                    repository_data.append((repo.name, repo.description, code_size))
            except Exception as e:
                print(f"Failed to retrieve repository {repo.name}: {e}")

        # Sort the repository data by code size in descending order
        repository_data.sort(key=lambda x: x[2], reverse=True)

        return repository_data

    except Exception as e:
        print(f"Failed to retrieve user repositories: {e}")
        return []

def generate_gpt_prompt(repository_name):
    prompt = f"Repository Name: {repository_name}\n\n"
    prompt += "Question: Give me one repository which is the most complex in implementation?\nAnswer:"
    prompt += "Question: Justify your output more technically precise\nAnswer:"
    return prompt

def generate_gpt_response(prompt):
    response = openai.Completion.create(
        engine="text-davinci-001",
        prompt=prompt,
        max_tokens=100,
        temperature=0.7,
        n=1,
        stop=None,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()

def index(request):
    return render(request, 'index.html')

def search_repositories(request):
    repo_url = request.GET.get('repoUrl')
    username = extract_username_from_url(repo_url)
    extensions = [".html", ".css", ".scss", ".less", ".xml", ".json", ".yaml", ".yml", ".rst", ".tex", ".c", ".cpp", ".java", ".py", ".rb", ".php", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".swift", ".kt", ".scala", ".pl", ".lua", ".dart", ".cs", ".vb"]
    langchain = "python"
    repository_data = retrieve_user_repositories(username, extensions, langchain)

    results = []
    if repository_data:
        repository_name, repository_description, _ = repository_data[0]
        prompt = generate_gpt_prompt(repository_name)
        gpt_response = generate_gpt_response(prompt)
        gpt_response1 = generate_gpt_response(repository_description)

        results.append({'name': repository_name, 'description': gpt_response, 'prompt': gpt_response1})
    else:
        error_response = {'error': 'Repository not found'}
        return JsonResponse(error_response)

    return JsonResponse(results, safe=False)