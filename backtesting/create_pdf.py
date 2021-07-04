from fpdf import FPDF, HTMLMixin
from datetime import datetime
import pandas as pd
import bs4




class PDF(FPDF, HTMLMixin):
    def __init__(self, backcast):
        super().__init__()
        self.WIDTH = 210
        self.HEIGHT = 297
        self.backcast = backcast

    def header(self):
        self.set_font('Arial', 'B', 18)
        datestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"{self.backcast.strategy_name} Backtest Summary"
        self.cell(60, 1, title)
        self.ln(20)

    def summary(self):

        df = self.backcast.trades
        df['winning_trade'] = df['pct_change'].apply(lambda x: 1 if x > 0 else 0)
        wins = df[df['winning_trade'] == 1]
        loss = df[df['winning_trade'] == 0]
        num_wins = len(wins)
        num_loss = len(loss)
        win_pct = num_wins / (num_wins + num_loss)
        win_avg = wins['pct_change'].mean()
        win_max = wins['pct_change'].max()
        loss_avg = loss['pct_change'].mean()
        loss_max = loss['pct_change'].min()
        abs_return = self.backcast.capital - self.backcast.starting_capital
        pct_return = (self.backcast.capital - self.backcast.starting_capital) / self.backcast.starting_capital

        self.set_font('Arial', style='B', size=14)
        self.cell(w=0, txt='Summary Statistics')
        self.ln(10)
        self.set_font('Arial', size=10)
        self.cell(w=0, h=3, txt=f"Starting Capital: ${self.backcast.starting_capital}", ln=2)
        self.cell(w=0, h=3, txt=f"Ending Capital: ${int(self.backcast.capital)}", ln=2)
        self.cell(w=0, h=3, txt=f"Overall return: ${int(abs_return)}", ln=2)
        self.cell(w=0, h=3, txt=f"Percent return: {pct_return:.2%}", ln=2)
        self.ln(5)
        self.cell(w=0, h=3, txt=f"Wins: {num_wins}", ln=2)
        self.cell(w=0, h=3, txt=f"Win Ratio: {win_pct:.2%}", ln=2)
        self.cell(w=0, h=3, txt=f"Average Win: {win_avg:.2%}", ln=2)
        self.cell(w=0, h=3, txt=f"Largest Win: {win_max:.2%}", ln=2)
        self.ln(5)
        self.cell(w=0, h=3, txt=f"Losses: {num_loss}", ln=2)
        self.cell(w=0, h=3, txt=f"Average Loss: {loss_avg:.2%}", ln=2)
        self.cell(w=0, h=3, txt=f"Largest Loss: {loss_max:.2%}", ln=2)
        self.ln(5)
        self.cell(w=0, h=3, txt=f"Backtest Range: {self.backcast.start} to {self.backcast.end}", ln=2)
        self.cell(w=0, h=3, txt=f"Number of Candlesticks: {len(self.backcast.backcast_data)}", ln=2)
        self.cell(w=0, h=3, txt=f"Number of Trades: {len(self.backcast.trades)}", ln=2)
        self.cell(w=0, h=3, txt=f"Trade to Candlestick ratio: {len(self.backcast.trades)/len(self.backcast.backcast_data):.2}", ln=2)

        pd.set_option('display.max_colwidth', 40)
        return df

    def create_report(self):

        self.add_page()
        df = self.summary()

        # self.add_page()
        # html = df.to_html()
        # self.write_html(html)
        return