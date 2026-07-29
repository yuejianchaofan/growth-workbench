"""
Daily AI + Tech + Energy news updater for growth-workbench.
Fetches from HN (English tech) + 36kr/Solidot (Chinese tech/news).
Run by GitHub Actions daily at 08:00 Beijing time.
"""
import urllib.request, ssl, json, base64, re, random, datetime, os
from urllib.request import urlopen, Request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# ─────────────── News Fetchers ───────────────

def fetch_hn():
    """Hacker News top stories, broad tech/AI/energy keywords."""
    news = []
    try:
        resp = urlopen(urlopen('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10))
        ids = json.loads(resp.read())
    except:
        return news

    kw = ['ai', 'artificial', 'gpt', 'llm', 'model', 'openai', 'anthropic', 'gemini',
          'deepmind', 'chatgpt', 'claude', 'nvidia', 'agent', 'robot', 'copilot',
          'generative', 'diffusion', 'midjourney', 'neural', 'chip', 'semiconductor',
          'battery', 'solar', 'ev ', 'electric vehicle', 'energy', 'tesla', 'spacex',
          'quantum', 'fusion', 'renewable', 'climate tech', 'science breakthrough',
          'autonomous', 'drone', 'satellite', 'tech']

    for sid in ids[:100]:
        if len(news) >= 5:
            break
        try:
            item = json.loads(urlopen(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json', timeout=5).read())
            t = (item.get('title') or '').lower()
            if any(k in t for k in kw):
                dom = 'HN'
                if item.get('url'):
                    try:
                        dom = urlparse(item['url']).netloc.replace('www.', '').split('.')[0].title()
                    except:
                        pass
                news.append({'t': item['title'][:120], 's': dom})
        except:
            continue
    return news


def is_relevant(title, keywords):
    """Check if title contains any relevant keyword."""
    t = title.lower()
    return any(k in t for k in keywords)


def fetch_36kr():
    """36kr RSS - Chinese tech/business/AI/energy news."""
    news = []
    KW = ['ai', '人工智能', '大模型', 'gpt', '芯片', '新能源', '电池', '光伏', '储能',
          '电动车', '特斯拉', '比亚迪', '机器人', '自动驾驶', '量子', '卫星', '航天',
          '科技', '智能', '算力', 'gpu', 'nvidia', '英伟达', 'openai', '融资', '上市']
    try:
        req = Request('https://36kr.com/feed', headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req, timeout=15).read()
        root = ET.fromstring(data)
        for item in root.iter('item'):
            title = item.find('title')
            if title is not None and title.text:
                t = title.text.strip()
                if is_relevant(t, KW):
                    news.append({'t': t[:120], 's': '36氪'})
            if len(news) >= 5:
                break
    except Exception as e:
        print(f'  36kr error: {str(e)[:80]}')
    return news


def fetch_solidot():
    """Solidot RSS - Chinese geek/tech news (like Slashdot)."""
    news = []
    KW = ['ai', '人工智能', '芯片', '量子', '新能源', '电池', '科技', '机器人',
          '自动驾驶', '太空', '卫星', '开源', '模型', 'gpu', '安全', '隐私']
    try:
        req = Request('https://www.solidot.org/index.rss', headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req, timeout=15).read()
        root = ET.fromstring(data)
        for item in root.iter('item'):
            title = item.find('title')
            if title is not None and title.text:
                t = title.text.strip()
                if is_relevant(t, KW):
                    news.append({'t': t[:120], 's': 'Solidot'})
            if len(news) >= 3:
                break
    except Exception as e:
        print(f'  Solidot error: {str(e)[:80]}')
    return news


def fetch_all_news():
    """Combine all sources, deduplicate by title similarity."""
    all_news = fetch_hn() + fetch_36kr() + fetch_solidot()
    if not all_news:
        return []

    # Simple dedup: keep unique titles (first 60 chars as key)
    seen = set()
    unique = []
    for n in all_news:
        key = n['t'][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)
        if len(unique) >= 10:
            break
    return unique[:10]


# ─────────────── HTML Update ───────────────

def update_index():
    TOKEN = os.getenv('GH_TOKEN', '')
    REPO = 'yuejianchaofan/growth-workbench'
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def api(method, path, body=None):
        url = 'https://api.github.com' + path
        data = json.dumps(body).encode() if body else None
        h = {'Authorization': 'token ' + TOKEN, 'User-Agent': 'GH-Action', 'Accept': 'application/vnd.github+json'}
        if body:
            h['Content-Type'] = 'application/json'
        resp = urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), context=ctx)
        return json.loads(resp.read())

    # Download index.html
    print('Downloading index.html...')
    cur = api('GET', '/repos/' + REPO + '/contents/index.html')
    html_text = base64.b64decode(cur['content'].replace('\n', '')).decode('utf-8')
    sha = cur['sha']

    # Fetch news
    news = fetch_all_news()
    print(f'Fetched {len(news)} news items from all sources')

    if not news:
        print('No news fetched, aborting.')
        return

    # Build JS array
    lines = []
    for n in news:
        t = n['t'].replace('\\', '\\\\').replace("'", "\\'")
        s = n['s'].replace('\\', '\\\\').replace("'", "\\'")
        lines.append("  {t:'" + t + "', s:'" + s + "'},")

    new_block = 'const AI_NEWS = [\n' + '\n'.join(lines) + '\n];'
    html_text = re.sub(r'const AI_NEWS = \[[\s\S]*?\];', new_block, html_text, count=1)

    # Upload
    print('Uploading...')
    new_b64 = base64.b64encode(html_text.encode('utf-8')).decode()
    r = api('PUT', '/repos/' + REPO + '/contents/index.html', {
        'message': 'Daily AI+Tech+Energy refresh [' + datetime.date.today().isoformat() + ']',
        'content': new_b64,
        'sha': sha
    })
    print('OK: ' + r['content']['name'] + ' updated')

if __name__ == '__main__':
    update_index()
