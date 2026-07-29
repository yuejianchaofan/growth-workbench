"""
Daily AI content updater for growth-workbench.
Fetches latest AI news from free sources, generates prompt rotation.
Run by GitHub Actions daily at 08:00 Beijing time.
"""
import json, re, random, datetime, html
from urllib.request import urlopen, Request
from urllib.error import URLError

HTML_PATH = 'index.html'

# ─────────────────── AI News Fetcher ───────────────────
def fetch_hn_news():
    """Hacker News top stories, filtered for AI/ML keywords."""
    try:
        ids = json.loads(urlopen('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10).read())
    except:
        return []
    
    keywords = ['ai', 'artificial', 'gpt', 'llm', 'model', 'openai', 'anthropic',
                'gemini', 'deepmind', 'machine learning', 'neural', 'transformer',
                'chatgpt', 'claude', 'copilot', 'nvidia', 'gpu', 'cuda', 'robot',
                'autonomous', 'intelligence', 'agent', 'prompt', 'diffusion',
                'stable diffusion', 'midjourney', 'sora', 'generative']
    
    news = []
    fetched = 0
    for sid in ids[:80]:
        if len(news) >= 8:
            break
        try:
            item = json.loads(urlopen(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json', timeout=5).read())
        except:
            continue
        fetched += 1
        title = (item.get('title') or '').lower()
        if any(kw in title for kw in keywords):
            url = item.get('url', f'https://news.ycombinator.com/item?id={sid}')
            domain = 'HN'
            if 'url' in item and item['url']:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(item['url']).netloc.replace('www.', '').split('.')[0].title()
                except:
                    domain = 'HN'
            news.append({'t': item['title'][:120], 's': domain})
    return news

def fetch_reddit_news():
    """Reddit r/artificialintelligence hot posts."""
    try:
        req = Request('https://www.reddit.com/r/artificialintelligence/hot.json?limit=15',
                      headers={'User-Agent': 'growth-workbench/1.0'})
        data = json.loads(urlopen(req, timeout=10).read())
        posts = data['data']['children']
        news = []
        for p in posts:
            t = p['data']['title'][:120]
            if t.startswith('[D]') or t.startswith('[N]'):
                t = t[3:].strip()
            news.append({'t': t, 's': 'Reddit AI'})
            if len(news) >= 6:
                break
        return news
    except:
        return []

def fetch_news():
    """Combine sources, deduplicate, return top 10."""
    all_news = fetch_hn_news() + fetch_reddit_news()
    seen = set()
    unique = []
    for n in all_news:
        key = n['t'][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)
        if len(unique) >= 10:
            break
    return unique[:10]

# ─────────────────── AI Prompts Pool ───────────────────
PROMPT_POOL = [
    {'t':'角色设定法', 'd':'「你是一位懂心理学的读书博主，说话克制、有温度，别喊口号。帮我写一段 150 字开场白，劝一个总说没时间读书的人今晚翻两页。」先给身份、语气、受众，AI 输出立刻有味道。', 'c':'先给身份和语气，再开口要东西。'},
    {'t':'分步拆解法', 'd':'「我想整理这周读书笔记。第一步把 5 条划线按主题归类；第二步给每类写一句核心；第三步合成一段朋友圈文案。每步做完等我说继续。」大任务切成小步，边做边改。', 'c':'别一次要终稿，让 AI 陪你一步步走。'},
    {'t':'反向追问法', 'd':'「我打算辞掉稳定工作去摆摊，先别劝我，连续问我 4 个越来越尖锐的问题，逼我把风险想透。」让 AI 当诘问者，比直接要建议更能看清自己。', 'c':'会追问的提示词，比会下结论的更值钱。'},
    {'t':'对比分析框架', 'd':'「请对比公众号和视频号两个平台做读书内容的优劣势，从受众、变现、复利效应、内容门槛四个维度各自打分，满分 10 分。」让 AI 给你一张决策表而非一段废话。', 'c':'说「打分」，AI 会多一个维度思考。'},
    {'t':'反着写一遍', 'd':'「我刚才写了支持早起打卡的 3 个理由。现在请你帮我写一份反对早起打卡的 3 个理由，一样有说服力。」认知冲突出好内容。', 'c':'写完后让它反着写，你会看到自己忽略的东西。'},
    {'t':'限制条件法', 'd':'「用 50 个字解释什么是机会成本，不准出现经济学、理性人、边际这三个词。」限制越具体，输出越精炼。', 'c':'给 AI 太多空间它反而啰嗦，框死它。'},
    {'t':'类比生成法', 'd':'「把 AI 学习这个过程，打一个日常比喻，让完全不懂科技的 60 岁阿姨也能听懂。」好内容靠好比喻。', 'c':'比喻是理解的捷径，AI 比你更会打。'},
    {'t':'受众分层法', 'd':'「同一套读书方法论，分别写给大学生、职场新人、40 岁中年管理层看。三段语气完全不同。」一个主题三层表达。', 'c':'换受众就是换内容，一鱼多吃。'},
    {'t':'模板填空法', 'd':'「我发你一个公众号开头句式：[痛点场景]+[反常识观点]+[我的行动]。帮我按这个句式写三个不同的开头。」给模板比给主题更有效。', 'c':'AI 不怕模板，怕你说得太模糊。'},
    {'t':'最坏情况推演', 'd':'「我想每周在视频号发 3 条口播。请列出这个计划未来 3 个月可能出现的 5 种最坏情况，��按发生概率排序。」先看清所有坑再跳。', 'c':'让 AI 给你恐惧，比给你鸡汤有用。'},
    {'t':'删减法', 'd':'「这段 800 字的读书笔记，用 100 字重写。要求保留原意、删掉所有修饰词。」砍��来的才是精华。', 'c':'给 AI 一把剪刀，它会比你狠。'},
    {'t':'对话体创作', 'd':'「把这段科普写成两个朋友喝酒时的对话，一个懂一个不懂，来回 4 轮。」对抗性让内容天然有节奏。', 'c':'对话自带张力，自言自语最容易乏味。'},
    {'t':'场景化指令', 'd':'「别给我讲时间管理的理论。直接给我明天早上 6 点到 9 点的精确到 15 分钟的行动表。」抽象的建议无意义。', 'c':'越具体的指令，越能用的结果。'},
    {'t':'跨界迁移法', 'd':'「用军事战略里的火力侦察原则，拆解我这次视频号冷启动的 4 个关键步骤。」跨界类比让人眼前一亮。', 'c':'从其他领域借框架，比在旧领域打转强。'},
    {'t':'数据验证法', 'd':'「我写的干货文里列了 5 个论据。请你逐条指出其中缺乏数据支撑的点，并建议去哪里找对应的数据。」AI 擅长查漏补缺。', 'c':'让 AI 当质检员，别当吹捧者。'},
    {'t':'纠错前置法', 'd':'「先指出我这段草稿的 3 个最大问题。不要跳过任何一条，每一条都要给出具体修改建议。然后我再决定改不改。」说缺点比说优点难一万倍。', 'c':'把挑剔放在创作前，省十倍修改时间。'},
    {'t':'风格克隆法', 'd':'「分析下面 3 段文字的语言风格特征（用词习惯、句式长短、情绪温度），然后按同样的风格写一篇新的。」别让人一眼看出是 AI 写的。', 'c':'先解剖风格，再让 AI 戴上那个面具。'},
    {'t':'渐进式引导', 'd':'「我想学中医入门，但没有任何基础。先给我一个 5 天的极简起步计划，每天只做一件 15 分钟内能完成的事。」零基础最怕信息过载。', 'c':'每一步小到不可能失败，才真的会开始。'},
    {'t':'多视角辩论', 'd':'「就「AI 会不会取代人类创造力」这个话题，同时模仿艺术家、工程师、哲学家三个人的立场各自写一段。语气要像真人在吵。」观点在碰撞中成形。', 'c':'一个人想不明白的事，让三个 AI 吵一架。'},
    {'t':'隐藏指令法', 'd':'「接下来的对话里，每次我给出一个想法后，你除了回应我还要用[挑战]标签附上一条我没考虑到的风险。不用我每次问。」把挑剔变成默认模式。', 'c':'把规则悄悄埋进系统指令，比每次都提醒强。'},
    {'t':'悬念开场法', 'd':'「我想写一篇关于副业失败的文章。先用 50 字写一个悬疑感极强的开头，让读者非翻下去不可。不要直接说结论。」第一条钩子决定了打开率。', 'c':'前 3 句话没钩住，后面写得再好也白搭。'},
    {'t':'场景还原法', 'd':'「不要讲抽象道理。描述一个具体的人在具体的时刻做具体的动作，让道理自己浮现出来。主题是：坚持。」故事大于说教。', 'c':'好的道理不需要「说」，它自己会从场景里浮上来。'},
    {'t':'反差冲突法', 'd':'「给我 5 个你认为大多数人都同意但实际上完全错误的生活常识。每个用一句话颠覆，要有冲击力。」反直觉就是流量密码。', 'c':'你以为所有人都知道的事，其实最有反转空间。'},
    {'t':'行动锚定法', 'd':'「文章结尾不要写感悟，写一个明天早上就能做的、5 分钟以内的具体动作。读者需要的是一个抓手，不是一段感悟。」结尾不行动，等于白写。', 'c':'一篇文章的价值，最终体现在读者明天的行为里。'},
    {'t':'情绪曲线法', 'd':'「这是一篇关于焦虑的文章。帮我规划情绪节奏：开头（共情、确认焦虑）→ 中段（理性分析、拆解）→ 结尾（轻松、释放）。每段标注情绪温度 0-10。」情绪是有节奏的。', 'c':'读者的注意力跟情绪走，不是跟逻辑走。'},
    {'t':'提问链法', 'd':'「不要直接给出答案。连续问我 5 个递进的问题，让答案在我回答的过程中自然浮现。」最好的老师不会给你答案，他给你对的题目。', 'c':'引导式提问比任何答案都更值钱。'},
    {'t':'隐喻转化法', 'd':'「把区块链的工作原理用一个完全非技术的隐喻讲清楚。比喻不能是记账本、数据库、锁链这三个。」旧隐喻已经被用烂了。', 'c':'好隐喻让复杂概念变成身体感受。'},
    {'t':'五感描写法', 'd':'「描述一个图书馆的清晨，但不要写你看到的。写你听到的、闻到的、触摸到的。用三种非视觉的感官。」五感不全的文章是平的。', 'c':'别只写画面。声音、气味、触感才是沉浸感。'},
    {'t':'否定前置法', 'd':'「先列出读者对「冥想」最常见的 3 个误解，然后在开头逐条击破。写完误解再开始讲方法。」清空误解，才能装入新知。', 'c':'先告诉别人他要推翻的，他才愿意听新的。'},
    {'t':'极简重构法', 'd':'「把我这段 500 字的说明文改写成不超过 30 个字。要求保留核心信息，但去掉所有形容词、副词、连接词。像公式一样干净。」字数限制是最狠的编辑。', 'c':'能用 10 个字讲清的事，别用 100 个字。'}
]

def pick_daily_prompts():
    today = datetime.date.today()
    seed = today.toordinal()
    pool = list(PROMPT_POOL)
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[:3]

# ─────────────────── HTML Update ───────────────────
def format_news_js(news):
    lines = []
    for n in news:
        t = n['t'].replace("'", "\\'").replace('"', '\\"')
        s = n['s'].replace("'", "\\'").replace('"', '\\"')
        lines.append(f"  {{t:'{t}', s:'{s}'}},")
    return 'const AI_NEWS = [\n' + '\n'.join(lines) + '\n];'

def format_prompts_js(prompts):
    lines = []
    for p in prompts:
        t = p['t'].replace("'", "\\'").replace('"', '\\"')
        d = p['d'].replace("'", "\\'").replace('"', '\\"')
        c = p['c'].replace("'", "\\'").replace('"', '\\"')
        lines.append(f"  {{t:'{t}', d:'{d}', c:'{c}'}},")
    return 'const AI_PROMPTS = [\n' + '\n'.join(lines) + '\n];'

def update_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html_text = f.read()
    
    # Replace AI_NEWS
    news = fetch_news()
    if news:
        new_news = format_news_js(news)
        html_text = re.sub(
            r'const AI_NEWS = \[[\s\S]*?\];',
            new_news,
            html_text,
            count=1
        )
        print(f'Updated AI_NEWS: {len(news)} items')
    else:
        print('WARNING: No news fetched, keeping existing AI_NEWS')
    
    # Replace AI_PROMPTS
    prompts = pick_daily_prompts()
    new_prompts = format_prompts_js(prompts)
    html_text = re.sub(
        r'const AI_PROMPTS = \[[\s\S]*?\];',
        new_prompts,
        html_text,
        count=1
    )
    print(f'Updated AI_PROMPTS: {len(prompts)} items')
    
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_text)

if __name__ == '__main__':
    update_html()
