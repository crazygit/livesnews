## 财经新闻机器人

不定期推送当前热门的财经信息

### 配置环境变量
```bash
# telegram机器人的token
$ echo 'BOT_TOKEN=xxxxxxxxxxxxxxx' >> .env
# telegram channel id
$ echo 'CHANNEL_ID=xxxxxxxxxxxxxxx' >> .env
```

### 环境初始化

```bash
$ python -V
Python 3.7.0

# 安装依赖
$ pip install -r requirements.txt

# 运行服务
$ python news_bot.py
```

## 数据来源

* [雪球](https://xueqiu.com/today/#/livenews)

## Telegram Channel

<https://t.me/livenews_7x24>
