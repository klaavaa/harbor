import requests
import networkx as nx
from networkx.algorithms import community
import matplotlib.pyplot as plt
import pickle



def get_pr_edges(owner, repo, pr_number, token, pr_author):
    headers = {"Authorization": f"Bearer {token}"}
    edges = []

    r_reviews = requests.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                             headers=headers).json()
    for review in r_reviews:
        reviewer = review["user"]["login"]
        edges.append({"from": reviewer, "to": pr_author, "type": "review"})
        if review["state"] == "APPROVED":
            edges.append({"from": reviewer, "to": pr_author, "type": "approval"})

    r_comments = requests.get(f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
                              headers=headers).json()
    for comment in r_comments:
        commenter = comment["user"]["login"]
        edges.append({"from": commenter, "to": pr_author, "type": "comment"})

    return edges

def get_all_pr_edges(owner, repo, numofprs, token):
    pr_edges = []
    page = 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",
            "per_page": 100,
            "page": page
        }
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            print("Error:", r.status_code, r.text)
            break

        data = r.json()
        
        for pull in data:
            if "pull_request" in pull:
                if "number" not in pull: continue
                if "user" not in pull: continue
                if "login" not in pull["user"]: continue
                number = pull["number"]
                login = pull["user"]["login"]
                edge = get_pr_edges(owner, repo, number, token, login)
                if edge: 
                    pr_edges.append(edge)
            print("amount of prs got data from: ", len(pr_edges))
            if len(pr_edges) >= numofprs:
                break


        if len(pr_edges) >= numofprs:
            break

        page += 1
        

    return pr_edges

def get_pr_data(owner, repo, numofprs):
    with open("token.txt", "r") as token_file:
        token = token_file.read().strip()

    pr_edges = get_all_pr_edges(owner, repo, numofprs, token)
    with open(f"{owner}-{repo}", "wb+") as pr_data:
        pickle.dump(pr_edges, pr_data)


def graph_data(owner, repo):
    with open(f"{owner}-{repo}", "rb") as pr_data:
        pr_edges = pickle.load(pr_data)

    pr_edges = [x for x in pr_edges if len(x) > 0]

    fixed_edges = []
    for edge in pr_edges:
        for x in edge:
            if x["from"] == x["to"]: continue
            fixed_edges.append(x)
    G = nx.Graph()
    comment_count = {}
    review_count = {}
    approval_count = {}
    for edge in fixed_edges:
        key = (edge["from"], edge["to"]) if edge["from"] < edge["to"] else (edge["to"], edge["from"])
        if key not in comment_count:
            comment_count[key] = 0
        if key not in review_count:
            review_count[key] = 0
        if key not in approval_count:
            approval_count[key] = 0

        if edge["type"] == "comment":
            comment_count[key] += 1
        elif edge["type"] == "review":
            review_count[key] += 1
        elif edge["type"] == "approval":
            approval_count[key] += 1

    weights = {}
    for key in comment_count:
        weights[key] = comment_count[key]
    for key in review_count:
        weights[key] += review_count[key] * 3
    for key in approval_count:
        weights[key] += approval_count[key] * 5

    filtered_weights = {}
    for key in weights:
        if weights[key] > 10:
            filtered_weights[key] = weights[key]

    maxWeight = 0
    for key in filtered_weights:
        print(filtered_weights[key])
        maxWeight = max(filtered_weights[key], maxWeight)

    for (f, t) in filtered_weights:
        if f not in G.nodes:
            G.add_node(f)    
        if t not in G.nodes:
            G.add_node(t)

        filtered_weights[(f, t)] = filtered_weights[(f, t)] / maxWeight
        G.add_edge(f, t, weight=filtered_weights[(f, t)])

    # set up the plt figure
    plt.figure(figsize=(20, 20), facecolor='black')
    ax = plt.gca()
    ax.set_facecolor('black')

    # i found that the forceatlas2 layout looks best
    pos = nx.forceatlas2_layout(G, scaling_ratio=5, gravity=3)

    # color the nodes based on the community they belong in
    communities = community.greedy_modularity_communities(G)
    colors = plt.cm.tab20.colors
    color_map = {node: colors[i % 20] for i, community in enumerate(communities) for node in community}
    node_colors = [color_map[n] for n in G.nodes()]


    # draw labels for nodes with most connections
    top_nodes = sorted(G.degree, key=lambda x: x[1], reverse=True)[:10]
    labels = {n: n for n,_ in top_nodes}

    nx.draw_networkx_labels(G, pos, labels, font_size=12, font_color = 'white')
    nx.draw_networkx_edges(G, pos, width=0.2, edge_color="white", alpha=0.85)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors)

    plt.axis("off")
    plt.tight_layout()
    plt.show()



def main():
    # load data
    get_pr_data("psf", "requests", 500)  
    # display data
    graph_data("psf", "requests")
    #graph_data("pandas-dev", "pandas")


if __name__ == '__main__':
    main()