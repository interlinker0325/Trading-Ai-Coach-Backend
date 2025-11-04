"""
Seed script to populate initial course data
Run with: python -m app.scripts.seed_education_data
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import SessionLocal
from app.crud.education import create_course, get_courses, create_quiz, get_quizzes, create_playbook, get_playbooks
from app.schemas.education import (
    CourseCreate,
    LessonBase,
    LessonType,
    CourseLevel,
    QuizCreate,
    QuestionBase,
    QuestionType,
    PlaybookCreate,
    PlaybookStep,
)


def seed_education_data():
    """Seed initial course data"""
    db = SessionLocal()

    try:
        # Check if courses already exist
        existing_courses = get_courses(db, limit=1)
        if existing_courses:
            print("⚠️  Courses already exist in database. Skipping seed to avoid duplicates.")
            print("   To re-seed, first drop the tables or delete existing courses.")
            return
        # Courses data
        courses_data = [
            {
                "course": {
                    "title": "Stock Market Fundamentals",
                    "description": "Learn the basics of stock trading, market analysis, and investment strategies",
                    "level": CourseLevel.BEGINNER,
                    "duration": "3h 20min",
                    "modules": 8,
                    "category": "Stocks",
                    "instructor": "Jane Smith",
                    "icon": "TrendingUp",
                },
                "lessons": [
                    LessonBase(
                        title="Introduction to Stock Market",
                        duration="15 min",
                        type=LessonType.DESCRIPTION,
                        content="Introduction to Stock Market\n\nStocks represent ownership in a company. When you buy a stock, you become a shareholder and own a small piece of that company. The stock market is where these shares are bought and sold.\n\nKey concepts:\n- Stock exchanges (NYSE, NASDAQ) provide platforms for trading\n- Market participants include individual investors, institutions, brokers, and market makers\n- Trading hours typically follow market sessions (pre-market, regular hours, after-hours)\n- Basic terminology includes bid, ask, spread, volume, and market cap\n\nUnderstanding these fundamentals is essential for anyone looking to invest in stocks.",
                        order=1,
                    ),
                    LessonBase(
                        title="Market Participants & Exchanges",
                        duration="20 min",
                        type=LessonType.DESCRIPTION,
                        content="Market Participants\nMarket participants in the stock market include a diverse range of entities:\n\nIndividual Investors: Private persons who buy and sell stocks for personal investment and wealth growth.\n\nInstitutional Investors: Large entities such as mutual funds, pension funds, hedge funds, and insurance companies that trade large volumes of stocks.\n\nBrokers and Broker-Dealers: Brokers act as intermediaries for investors, executing buy and sell orders on their behalf, while broker-dealers can trade for themselves and others.\n\nMarket Makers and Dealers: Firms that provide liquidity by continuously quoting buy and sell prices, helping to reduce price volatility.\n\nPortfolio Managers: Professionals who manage investment portfolios for institutional or individual clients, making buy and sell decisions.\n\nInvestment Bankers: They facilitate companies going public (IPOs), mergers, and acquisitions, assisting in compliance with regulatory authorities.\n\nCustodians and Depository Participants: Institutions that hold and safeguard securities on behalf of investors and facilitate the transfer of securities.\n\nArbitrageurs and Algorithmic Traders: Those who seek to profit from price inefficiencies and help maintain market efficiency by trading at high speeds.\n\nRegulators and Government Entities: Ensure markets operate fairly and transparently under established laws and regulations.\n\nStock Exchanges\nStock exchanges are organized marketplaces where stocks and other securities are traded between buyers and sellers. Key points about exchanges:\n\nThey provide platforms for companies to raise capital by issuing shares in the primary market (e.g., IPOs).\n\nAfter issuance, shares trade in the secondary market where investors buy and sell among themselves.\n\nExchanges match buy and sell orders electronically or on physical trading floors (e.g., NYSE).\n\nExchanges rely on market makers to maintain liquidity and facilitate smooth price discovery.\n\nExamples of major exchanges include the New York Stock Exchange (NYSE), Nasdaq, and many others worldwide.\n\nExchanges charge transaction fees for facilitating trades.\n\nTogether, these market participants and exchanges create a dynamic ecosystem where capital flows efficiently from investors to companies, supporting economic growth and investment opportunities for the public. This system is regulated to protect investors and ensure transparency and fairness in trading.",
                        order=2,
                    ),
                    LessonBase(
                        title="Stock Analysis Fundamentals",
                        duration="25 min",
                        type=LessonType.DESCRIPTION,
                        content="Stock Analysis Fundamentals\n\nThere are two main approaches to analyzing stocks:\n\nFundamental Analysis\n- Examines a company's financial health, earnings, revenue, and growth potential\n- Uses financial statements (income statement, balance sheet, cash flow statement)\n- Calculates key ratios like P/E, P/B, ROE, and debt-to-equity\n- Considers industry trends, competitive position, and management quality\n- Aims to determine intrinsic value of the stock\n\nTechnical Analysis\n- Studies price charts, patterns, and trading volume\n- Uses indicators like moving averages, RSI, MACD, and Bollinger Bands\n- Identifies support and resistance levels\n- Looks for trends and momentum\n- Aims to predict short-term price movements\n\nBoth approaches can be valuable. Many successful investors combine elements of both fundamental and technical analysis.",
                        order=3,
                    ),
                    LessonBase(
                        title="Understanding Stock Prices & Quotes",
                        duration="30 min",
                        type=LessonType.DESCRIPTION,
                        content="Understanding Stock Prices & Quotes\n\nStock quotes display real-time information about a stock's trading activity:\n\nBid Price: The highest price a buyer is willing to pay\nAsk Price: The lowest price a seller is willing to accept\nSpread: The difference between bid and ask prices\nLast Price: The most recent transaction price\n\nVolume shows how many shares were traded. High volume often indicates strong interest or significant news.\n\nPre-market and after-hours trading allow trading outside regular market hours, typically with lower liquidity.\n\nLevel 2 order books show deeper market depth, displaying all bids and asks at different price levels.",
                        order=4,
                    ),
                    LessonBase(
                        title="Dividends & Stock Splits",
                        duration="20 min",
                        type=LessonType.DESCRIPTION,
                        content="Dividends & Stock Splits\n\nDividends are payments made by companies to shareholders, usually from profits. Types include:\n- Cash dividends: Regular payments per share\n- Stock dividends: Additional shares instead of cash\n\nDividend yield = Annual dividend per share / Stock price\n\nStock splits increase the number of shares while maintaining the same total value. A 2-for-1 split doubles your shares but halves the price per share.\n\nThe ex-dividend date determines who receives the dividend. You must own the stock before this date.\n\nBoth dividends and splits affect shareholder value and can impact investment strategies.",
                        order=5,
                    ),
                    LessonBase(
                        title="Investment Strategies",
                        duration="35 min",
                        type=LessonType.DESCRIPTION,
                        content="Investment Strategies\n\nCommon investment approaches include:\n\nBuy and Hold: Long-term ownership regardless of short-term volatility\n- Focuses on quality companies with strong fundamentals\n- Requires patience and discipline\n\nDollar-Cost Averaging: Investing fixed amounts regularly\n- Reduces impact of market timing\n- Helps build positions gradually\n\nValue Investing: Buying undervalued stocks\n- Seeks stocks trading below intrinsic value\n- Popularized by Warren Buffett\n\nGrowth Investing: Targeting companies with high growth potential\n- Focuses on revenue and earnings growth\n- Higher risk, potentially higher returns\n\nDividend Investing: Building income through dividends\n- Targets stable companies with consistent dividends\n- Provides regular income stream\n\nChoose a strategy that aligns with your risk tolerance, time horizon, and financial goals.",
                        order=6,
                    ),
                    LessonBase(
                        title="Building Your First Portfolio",
                        duration="30 min",
                        type=LessonType.DESCRIPTION,
                        content="Building Your First Portfolio\n\nKey principles for portfolio construction:\n\nDiversification\n- Spread investments across different sectors and industries\n- Reduces risk by avoiding concentration in one area\n- Can include stocks, bonds, ETFs, and other assets\n\nAsset Allocation\n- Determine the mix of stocks, bonds, and cash based on your risk tolerance\n- Younger investors may favor more stocks for growth\n- Older investors may prefer more bonds for stability\n\nRisk Management\n- Never invest more than you can afford to lose\n- Set stop-losses if trading actively\n- Review and adjust positions periodically\n\nRebalancing\n- Periodically adjust your portfolio back to target allocation\n- Takes profits from winners, adds to underperformers\n- Maintains your desired risk level\n\nTracking Performance\n- Monitor your portfolio regularly\n- Compare returns to benchmarks\n- Adjust strategy based on results and changing goals",
                        order=7,
                    ),
                    LessonBase(
                        title="Portfolio Management Best Practices",
                        duration="30 min",
                        type=LessonType.DESCRIPTION,
                        content="Portfolio Management Best Practices\n\nEffective portfolio management involves:\n\nRegular Review\n- Monthly or quarterly assessment of holdings\n- Check performance against goals and benchmarks\n- Identify underperforming positions\n\nRisk Assessment\n- Understand your risk tolerance\n- Adjust portfolio as circumstances change\n- Use position sizing to control risk\n\nTax Considerations\n- Understand tax implications of trades\n- Consider tax-loss harvesting\n- Utilize tax-advantaged accounts when possible\n\nContinuous Learning\n- Stay informed about market trends\n- Read company reports and financial news\n- Learn from both successes and mistakes\n\nLong-term Perspective\n- Avoid emotional trading decisions\n- Stick to your investment plan\n- Focus on long-term wealth building rather than short-term gains",
                        order=8,
                    ),
                ],
            },
            {
                "course": {
                    "title": "Options Trading Mastery",
                    "description": "Advanced options strategies, Greeks, and risk management techniques",
                    "level": CourseLevel.ADVANCED,
                    "duration": "5h 15min",
                    "modules": 11,
                    "category": "Options",
                    "instructor": "Mike Johnson",
                    "icon": "Target",
                },
                "lessons": [
                    LessonBase(title="Options Basics", duration="20 min", type=LessonType.DESCRIPTION, order=1),
                    LessonBase(title="The Greeks Explained", duration="30 min", type=LessonType.DESCRIPTION, order=2),
                    LessonBase(title="Covered Calls Strategy", duration="25 min", type=LessonType.DESCRIPTION, order=3),
                    LessonBase(title="Cash-Secured Puts (CSP)", duration="30 min", type=LessonType.DESCRIPTION, order=4),
                    LessonBase(title="Straddles & Strangles", duration="30 min", type=LessonType.DESCRIPTION, order=5),
                    LessonBase(title="Iron Condors & Butterflies", duration="35 min", type=LessonType.DESCRIPTION, order=6),
                    LessonBase(title="Risk Management in Options", duration="30 min", type=LessonType.DESCRIPTION, order=7),
                    LessonBase(title="Volatility Trading", duration="25 min", type=LessonType.DESCRIPTION, order=8),
                    LessonBase(title="Options Assignment & Exercise", duration="20 min", type=LessonType.DESCRIPTION, order=9),
                    LessonBase(title="Options Portfolio Management", duration="30 min", type=LessonType.DESCRIPTION, order=10),
                    LessonBase(title="Building Options Strategies", duration="40 min", type=LessonType.DESCRIPTION, order=11),
                ],
            },
            {
                "course": {
                    "title": "Cryptocurrency Trading",
                    "description": "Digital assets, DeFi, and crypto market dynamics",
                    "level": CourseLevel.INTERMEDIATE,
                    "duration": "45 min",
                    "modules": 2,
                    "category": "Crypto",
                    "instructor": "Sarah Chen",
                    "icon": "DollarSign",
                },
                "lessons": [
                    LessonBase(title="Crypto Basics & Wallets", duration="25 min", type=LessonType.DESCRIPTION, order=1),
                    LessonBase(title="Trading Platforms", duration="20 min", type=LessonType.DESCRIPTION, order=2),
                ],
            },
            {
                "course": {
                    "title": "Futures Trading Essentials",
                    "description": "Master futures contracts, hedging, and market speculation strategies",
                    "level": CourseLevel.ADVANCED,
                    "duration": "1h 30min",
                    "modules": 3,
                    "category": "Futures",
                    "instructor": "Robert Anderson",
                    "icon": "TrendingUp",
                },
                "lessons": [
                    LessonBase(title="Understanding Futures Contracts", duration="25 min", type=LessonType.DESCRIPTION, order=1),
                    LessonBase(title="Futures vs Options", duration="30 min", type=LessonType.DESCRIPTION, order=2),
                    LessonBase(title="Hedging Strategies", duration="35 min", type=LessonType.DESCRIPTION, order=3),
                ],
            },
            {
                "course": {
                    "title": "Forex & Commodities",
                    "description": "Currency pairs, commodity markets, and global economics",
                    "level": CourseLevel.ADVANCED,
                    "duration": "45 min",
                    "modules": 2,
                    "category": "Forex",
                    "instructor": "Emma Wilson",
                    "icon": "Zap",
                },
                "lessons": [
                    LessonBase(title="Forex Market Basics", duration="20 min", type=LessonType.DESCRIPTION, order=1),
                    LessonBase(title="Currency Pairs Explained", duration="25 min", type=LessonType.DESCRIPTION, order=2),
                ],
            },
        ]

        # Create courses
        for course_data in courses_data:
            course_create = CourseCreate(**course_data["course"], lessons=course_data["lessons"])
            create_course(db, course_create)
            print(f"✓ Created course: {course_data['course']['title']}")

        print("\n✅ Course data seeded successfully!")

        # Check if quizzes already exist
        existing_quizzes = get_quizzes(db, limit=1)
        if existing_quizzes:
            print("\n⚠️  Quizzes already exist in database. Skipping quiz seed to avoid duplicates.")
        else:
            # Quizzes data
            quizzes_data = [
            {
                "title": "Stock Market Basics Quiz",
                "description": "Test your knowledge of stock market fundamentals",
                "category": "Stocks",
                "questions": [
                    QuestionBase(
                        question="What is the P/E ratio?",
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        options=[
                            "Price to Earnings",
                            "Profit to Equity",
                            "Price to Equity",
                            "Profit to Earnings",
                        ],
                        correct_answer=0,
                        order=1,
                        explanation="P/E ratio stands for Price to Earnings, which is calculated by dividing a company's stock price by its earnings per share. It helps investors assess whether a stock is overvalued or undervalued relative to its earnings.",
                    ),
                    QuestionBase(
                        question="A higher P/E ratio always means a stock is overvalued.",
                        question_type=QuestionType.TRUE_FALSE,
                        options=None,
                        correct_answer=False,
                        order=2,
                        explanation="A high P/E ratio doesn't always mean a stock is overvalued. It could indicate strong growth prospects, market confidence, or industry norms. Context and comparison with peers are important when evaluating P/E ratios.",
                    ),
                    QuestionBase(
                        question="Which factors affect stock prices? (Select all that apply)",
                        question_type=QuestionType.MULTIPLE_SELECT,
                        options=[
                            "Company earnings",
                            "Market sentiment",
                            "Interest rates",
                            "Weather",
                        ],
                        correct_answer=[0, 1, 2],
                        order=3,
                        explanation="Stock prices are affected by company earnings (financial performance), market sentiment (investor emotions and expectations), and interest rates (affecting borrowing costs and investment attractiveness). Weather generally doesn't directly affect stock prices, though it might indirectly impact certain sectors like agriculture or tourism.",
                    ),
                ],
            },
            {
                "title": "Options Trading Quiz",
                "description": "Test your understanding of options trading concepts",
                "category": "Options",
                "questions": [
                    QuestionBase(
                        question="What happens to option value as expiration approaches?",
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        options=[
                            "Increases",
                            "Decreases",
                            "Stays same",
                            "Becomes negative",
                        ],
                        correct_answer=1,
                        order=1,
                        explanation="Option value decreases as expiration approaches due to time decay (theta). The time value component of an option erodes as the expiration date gets closer, especially in the final weeks and days before expiration.",
                    ),
                    QuestionBase(
                        question="You can only exercise American options at expiration.",
                        question_type=QuestionType.TRUE_FALSE,
                        options=None,
                        correct_answer=False,
                        order=2,
                        explanation="American options can be exercised at any time before or at expiration, giving holders flexibility. European options, in contrast, can only be exercised at expiration. This difference affects option pricing and trading strategies.",
                    ),
                ],
            },
            ]

            # Create quizzes
            for quiz_data in quizzes_data:
                quiz_create = QuizCreate(
                    title=quiz_data["title"],
                    description=quiz_data["description"],
                    category=quiz_data["category"],
                    questions=quiz_data["questions"],
                )
                create_quiz(db, quiz_create)
                print(f"✓ Created quiz: {quiz_data['title']}")

            print("\n✅ Quiz data seeded successfully!")

        # Check if playbooks already exist
        existing_playbooks = get_playbooks(db, limit=1)
        if existing_playbooks:
            print("\n⚠️  Playbooks already exist in database. Skipping playbook seed to avoid duplicates.")
        else:
            # Playbooks data
            playbooks_data = [
                {
                    "title": "Day Trading Momentum Strategy",
                    "description": "Capture intraday momentum moves with entry and exit signals",
                    "category": "Stocks",
                    "level": CourseLevel.INTERMEDIATE,
                    "icon": "TrendingUp",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Identify High Volume Stocks",
                            description="Scan for stocks with volume 50% above average",
                            details="Use a scanner to find stocks trading with significantly higher volume than their 20-day average. This indicates strong institutional interest.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Confirm Trend Direction",
                            description="Verify price is above key moving averages",
                            details="Check that price is above both 9 EMA and 21 EMA on the 5-minute chart. This confirms bullish momentum.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Entry Signal",
                            description="Buy on pullback to support with bullish candlestick",
                            details="Wait for price to pull back to the 9 EMA or a key support level, then enter when you see a bullish engulfing or hammer candlestick pattern.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Set Stop Loss",
                            description="Place stop loss below the recent swing low",
                            details="Set your stop loss 1-2 cents below the most recent swing low to limit downside risk.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Take Profit Targets",
                            description="Scale out at 2:1 and 3:1 risk-reward ratios",
                            details="Take partial profits at 2R (2x your risk) and let the rest run to 3R or trail stop for larger gains.",
                        ),
                    ],
                },
                {
                    "title": "Options Wheel Strategy",
                    "description": "Generate consistent income through covered calls and cash-secured puts",
                    "category": "Options",
                    "level": CourseLevel.INTERMEDIATE,
                    "icon": "Target",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Select Quality Underlying",
                            description="Choose stocks you wouldn't mind owning long-term",
                            details="Pick stocks with strong fundamentals, good liquidity, and IV rank above 30% for better premium.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Sell Cash-Secured Put",
                            description="Sell puts at strike price 5-10% below current price",
                            details="Sell puts 30-45 DTE at a strike 5-10% OTM. Aim for 0.5-1% monthly return on capital.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Manage Assignment Risk",
                            description="Roll or take assignment if price approaches strike",
                            details="If price drops toward your strike, roll down and out for credit. If assigned, move to step 4.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Sell Covered Calls",
                            description="Sell calls above your cost basis",
                            details="After assignment, sell calls 30-45 DTE at strikes above your cost basis. Target 0.5-1% monthly return.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Repeat Cycle",
                            description="Continue the wheel strategy or close positions",
                            details="If called away, repeat from step 2. If not, continue selling calls and collect premium.",
                        ),
                    ],
                },
                {
                    "title": "Crypto Breakout Strategy",
                    "description": "Trade cryptocurrency breakouts from consolidation patterns",
                    "category": "Crypto",
                    "level": CourseLevel.BEGINNER,
                    "icon": "Zap",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Identify Consolidation",
                            description="Find coins trading in tight ranges for 3-7 days",
                            details="Look for coins that have been trading sideways in a tight range, forming a base pattern like triangles or rectangles.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Watch for Volume Spike",
                            description="Monitor for sudden volume increase",
                            details="A breakout with high volume (2-3x average) is more likely to sustain. Low volume breakouts often fail.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Enter on Breakout",
                            description="Buy when price breaks above resistance with volume",
                            details="Enter a long position when price breaks above the consolidation high with confirming volume. Use a limit order slightly above the breakout level.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Set Stop Loss",
                            description="Place stop below the consolidation low",
                            details="Set your stop loss just below the consolidation pattern low to protect against false breakouts.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Take Profits",
                            description="Scale out at 1.5x and 2x the pattern height",
                            details="Calculate the pattern height and take profits at 1.5x and 2x that distance. Trailing stops can capture larger moves.",
                        ),
                    ],
                },
                {
                    "title": "Forex Range Trading",
                    "description": "Profit from currency pairs trading in defined ranges",
                    "category": "Forex",
                    "level": CourseLevel.BEGINNER,
                    "icon": "DollarSign",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Identify Range Boundaries",
                            description="Mark clear support and resistance levels",
                            details="Use horizontal lines to identify clear support (lowest swing low) and resistance (highest swing high) over the last 20-50 candles.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Confirm Range is Active",
                            description="Ensure price respects boundaries multiple times",
                            details="Price should have bounced off support and resistance at least 2-3 times each. More touches = stronger levels.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Buy at Support",
                            description="Enter long when price reaches support",
                            details="Wait for price to touch support and show bullish reversal signals (engulfing, hammer, etc.). Enter with a limit order.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Sell at Resistance",
                            description="Take profits when price reaches resistance",
                            details="Set your take profit just below resistance. Consider taking partial profits at 50% and letting the rest run.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Exit on Breakout",
                            description="Close positions if range breaks",
                            details="If price breaks above resistance with volume, consider holding for trend continuation. If below support, exit immediately.",
                        ),
                    ],
                },
                {
                    "title": "Swing Trading Pullback Strategy",
                    "description": "Buy quality stocks on pullbacks during uptrends",
                    "category": "Stocks",
                    "level": CourseLevel.ADVANCED,
                    "icon": "BarChart3",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Identify Uptrending Stock",
                            description="Find stocks in clear uptrend with higher highs and lows",
                            details="Look for stocks making higher highs and higher lows on the daily chart. Ensure the 50 SMA is above 200 SMA.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Wait for Pullback",
                            description="Wait for price to pull back to key support",
                            details="Price should pull back to the 20 EMA, 50 SMA, or a previous support level. Ideal pullback is 5-15%.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Confirm Reversal Signal",
                            description="Look for bullish reversal patterns",
                            details="Wait for bullish candlestick patterns (hammer, engulfing, doji) or bullish divergence on RSI.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Enter Position",
                            description="Buy on confirmation with proper position sizing",
                            details="Enter with 50% of position on reversal confirmation. Add remaining 50% on break above recent high.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Manage Trade",
                            description="Trail stop loss and take profits at resistance",
                            details="Move stop loss to breakeven after 3% gain. Trail stop below recent swing lows. Take profits at key resistance levels.",
                        ),
                    ],
                },
                {
                    "title": "Options Iron Condor",
                    "description": "Neutral strategy to profit from low volatility",
                    "category": "Options",
                    "level": CourseLevel.ADVANCED,
                    "icon": "Target",
                    "steps": [
                        PlaybookStep(
                            step=1,
                            title="Select High IV Rank Underlying",
                            description="Choose stocks with IV rank above 50%",
                            details="Higher IV means higher premiums. Select stocks with IV rank above 50% for better premium collection.",
                        ),
                        PlaybookStep(
                            step=2,
                            title="Identify Expected Range",
                            description="Determine where price will likely stay",
                            details="Use technical analysis to identify support and resistance. Price should stay within this range for the trade duration.",
                        ),
                        PlaybookStep(
                            step=3,
                            title="Sell Call Spread",
                            description="Sell OTM call spread above current price",
                            details="Sell a call spread 30-45 DTE with strikes above resistance. Aim for 1/3 the width of the spread in premium.",
                        ),
                        PlaybookStep(
                            step=4,
                            title="Sell Put Spread",
                            description="Sell OTM put spread below current price",
                            details="Sell a put spread with strikes below support. Same DTE and premium target as call spread.",
                        ),
                        PlaybookStep(
                            step=5,
                            title="Manage and Close",
                            description="Close at 50% profit or 21 DTE",
                            details="Close the entire position when you've collected 50% of max profit, or when 21 DTE remains. Roll if one side is threatened.",
                        ),
                    ],
                },
            ]

            # Create playbooks
            for playbook_data in playbooks_data:
                playbook_create = PlaybookCreate(**playbook_data)
                create_playbook(db, playbook_create)
                print(f"✓ Created playbook: {playbook_data['title']}")

            print("\n✅ Playbook data seeded successfully!")

    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_education_data()

