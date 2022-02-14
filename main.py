import argparse
from bs4 import BeautifulSoup as bs
from distutils.util import strtobool
import os
from pathlib import Path
import ssl
import urllib.request
import webbrowser


parser = argparse.ArgumentParser()
parser.add_argument("--keywords", nargs='+', help="The keywords included in the search")
parser.add_argument("--url", type=str, default="https://arxiv.org/list/cs/new", help="The website to seach")
parser.add_argument('--search_title', default=True, type=lambda x: bool(strtobool(str(x))), help="Search title?")  # strtobool: True values (int: 1) are y, yes, t, true, on and 1. False values (int: 0) are n, no, f, false, off and 0"
parser.add_argument('--search_abstract', default=True, type=lambda x: bool(strtobool(str(x))), help="Search abstract?")
parser.add_argument("--date_placeholder", type=str, default="DATE_PLACEHOLDER", help="Must be found in `news_template.html`, for substitution")
parser.add_argument("--article_placeholder", type=str, default="ARTICLE_PLACEHOLDER", help="Must be found in `news_template.html`, for substitution")

args = parser.parse_args()

# for readability
URL = args.url
KEYWORDS = args.keywords
SEARCH_TITLE = args.search_title
SEARCH_ABSTRACT = args.search_abstract
DATE_PLACEHOLDER = args.date_placeholder
ARTICLE_PLACEHOLDER = args.article_placeholder

# where to read the html template from, and write the new file to
# currently the same as `main.py` script folder
HTML_DIR = Path(os.path.realpath(__file__)).parent

# must choose at least one search field out of {title, abstract} 
assert SEARCH_TITLE or SEARCH_ABSTRACT

# must choose at least one search keyword
assert isinstance(KEYWORDS, list)
assert len(KEYWORDS) > 0


def read_webpage(url):
    """
    Read webpage contents

    use a 'context' that does not verify SSL certification to avoid the error:
    "urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>"
    """
    
    page = urllib.request.urlopen(url, context=ssl._create_unverified_context())
    soup = bs(page, features="html.parser")
    content = soup.body.find("div", {'id': 'content'})
    return content


def extract_info_from_webpage(url):
    """
    Extract information from webpage contents.
    
    Includes:
    - info_date: the date of the arXiv publications
    - info_dt: the arXiv numbers
    - info_dd: the title, author, subjects, abstract

    [info_dt]
    <dt><a name="item1">[1]</a>   <span class="list-identifier"><a href="/abs/2202.04643" title="Abstract">arXiv:2202.04643</a> [<a href="/pdf/2202.04643" title="Download PDF">pdf</a>, <a href="/format/2202.04643" title="Other formats">other</a>]</span></dt>
    
    [info_dd]
    <dd>
    <div class="meta">
    <div class="list-title mathjax">
    <span class="descriptor">Title:</span> Dimensionally Consistent Learning with Buckingham Pi
    </div>
    <div class="list-authors">
    <span class="descriptor">Authors:</span>
    <a href="/search/cs?searchtype=author&amp;query=Bakarji%2C+J">Joseph Bakarji</a>, 
    <a href="/search/cs?searchtype=author&amp;query=Callaham%2C+J">Jared Callaham</a>, 
    <a href="/search/cs?searchtype=author&amp;query=Brunton%2C+S+L">Steven L. Brunton</a>, 
    <a href="/search/cs?searchtype=author&amp;query=Kutz%2C+J+N">J. Nathan Kutz</a>
    </div>
    <div class="list-subjects">
    <span class="descriptor">Subjects:</span> <span class="primary-subject">Machine Learning (cs.LG)</span>; Computational Engineering, Finance, and Science (cs.CE); Computational Physics (physics.comp-ph)

    </div>
    <p class="mathjax">In the absence of governing equations, dimensional analysis is a robust
    technique for extracting insights and finding symmetries in physical systems.
    Given measurement variables and parameters, the Buckingham Pi theorem provides
    a procedure for finding a set of dimensionless groups that spans the solution.
    </p>
    </div>
    </dd>
    """
    
    content = read_webpage(url)
    info_date = content.find("h3").text.split(',')[1]
    info_dt = content.dl.find_all("dt")
    info_dd = content.dl.find_all("dd")

    return info_date, info_dt, info_dd


def main():
    
    # read the html template
    # information for each article will be added to this html file
    with open(Path(HTML_DIR, "news_template.html"), "r") as f:
        news = f.read()

    # `DATE_PLACEHOLDER` and `ARTICLE_PLACEHOLDER` must match a section found in `news_template.html`
    assert DATE_PLACEHOLDER in news 
    assert ARTICLE_PLACEHOLDER in news

    # this snippet defines the collapsible button
    snippet = """
    <button type="button" class="collapsible">TITLE</button>
    <div class="content">
    <p> <a href="LINK" target="_blank">LINK</a> </p>
    <p>ABSTRACT</p>
    </div>
    """

    # extract relevant information from the webpage into a dataframe
    info_date, \
    info_dt, \
    info_dd = extract_info_from_webpage(URL)

    # process info 
    for i in range(len(info_dd)):
        
        title = info_dd[i].find("div", {"class": "list-title mathjax"}).text.strip().replace("Title: ", "")
        abstract = info_dd[i].find("p", {"class": "mathjax"}).text.strip().replace("\n", " ")
        number = info_dt[i].text.strip().split(" ")[2].split(":")[1]
        link = f"https://arxiv.org/abs/{number}"

        search_string = ""
        search_string += title if SEARCH_TITLE is True else " "
        search_string += abstract if SEARCH_ABSTRACT is True else ""
            
        for keyword in KEYWORDS:
            if keyword.lower() in search_string.lower():
                article = snippet
                article = article.replace("TITLE", title)
                article = article.replace("LINK", link)
                article = article.replace("ABSTRACT", abstract)
                news = news.replace(ARTICLE_PLACEHOLDER, article + ARTICLE_PLACEHOLDER)

        news = news.replace(DATE_PLACEHOLDER, info_date)
        news.replace(ARTICLE_PLACEHOLDER, "")


    # save the html news file
    html_news_file = Path(HTML_DIR, "news.html")
    os.system("rm {}".format(html_news_file))
    with open(html_news_file, "w") as f:
        f.write(news)

    # open the html news file in the browser
    webbrowser.open_new_tab("file://" + str(html_news_file.resolve()))



if __name__ == "__main__":

    print("Searching {URL} for keywords {KEYWORDS} in {FIELDS}".format(
        URL=URL, 
        KEYWORDS=KEYWORDS, 
        FIELDS='{' + ('title' if SEARCH_TITLE else '') 
                    + (', ' if SEARCH_TITLE and SEARCH_ABSTRACT else '') 
                    + ('abstract' if SEARCH_ABSTRACT else '') + '}...'), end=' '
    )

    main()

    print("Done!")