from django.shortcuts import render, redirect
from .forms import HisseForm
from django.http import JsonResponse
import json
import os
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from ta.momentum import RSIIndicator, ROCIndicator, stochrsi
from ta.trend import MACD, EMAIndicator, SMAIndicator, CCIIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import datetime
from plotly.subplots import make_subplots
import traceback


def get_scalar_value(series_or_scalar):
    """Safely extracts a scalar value from a Pandas Series or returns the scalar itself."""
    if isinstance(series_or_scalar, pd.Series):
        if not series_or_scalar.empty:
            return series_or_scalar.item()
        return None
    return series_or_scalar


def anasayfa(request):
    if request.method == 'POST':
        form = HisseForm(request.POST)
        if form.is_valid():
            kod = form.cleaned_data['kod'].strip().upper()
            baslangic_tarihi = form.cleaned_data.get('baslangic_tarihi')
            if not kod.endswith('.IS'):
                kod += '.IS'
            if baslangic_tarihi:
                return redirect(f'/analiz/{kod}?start={baslangic_tarihi.strftime("%Y-%m-%d")}')
            else:
                return redirect(f'/analiz/{kod}')
    else:
        form = HisseForm()
    return render(request, 'analiz/anasayfa.html', {'form': form})


def autocomplete(request):
    q = request.GET.get('q', '').strip().upper()
    path = os.path.join(os.path.dirname(__file__), 'utils', 'hisseler.json')
    if not os.path.exists(path):
        return JsonResponse([], safe=False)

    with open(path, encoding='utf-8') as f:
        hisseler = json.load(f)

    matches = []
    for h in hisseler:
        short_kod = h.get('short', '').split('\n')[0].strip().upper()
        name = h.get('short', '').split('\n')[1].strip() if '\n' in h.get('short', '') else ''
        if q in short_kod or q in name.upper():
            starts_with_score = 0
            if short_kod.startswith(q): starts_with_score += 2
            if name.upper().startswith(q): starts_with_score += 1
            matches.append({'short': short_kod, 'name': name, 'score': starts_with_score})

    sorted_results = sorted(matches, key=lambda x: -x['score'])
    return JsonResponse([{'short': m['short'], 'name': m['name']} for m in sorted_results], safe=False)


def analiz_sayfasi(request, kod):
    context = {}
    baslangic_tarihi_str = request.GET.get('start')
    baslangic_tarihi = None
    if baslangic_tarihi_str:
        try:
            baslangic_tarihi = datetime.datetime.strptime(baslangic_tarihi_str, '%Y-%m-%d').date()
        except ValueError:
            context['hata'] = 'Geçersiz başlangıç tarihi formatı. Lütfen YYYY-AA-GG formatını kullanın.'

    if request.method == 'POST':
        form = HisseForm(request.POST)
        if form.is_valid():
            new_kod = form.cleaned_data['kod'].strip().upper()
            new_baslangic_tarihi = form.cleaned_data.get('baslangic_tarihi')
            if not new_kod.endswith('.IS'):
                new_kod += '.IS'
            if new_baslangic_tarihi:
                return redirect(f'/analiz/{new_kod}?start={new_baslangic_tarihi.strftime("%Y-%m-%d")}')
            else:
                return redirect(f'/analiz/{new_kod}')
    else:
        initial_data = {'kod': kod.replace('.IS', ''), 'baslangic_tarihi': baslangic_tarihi}
        form = HisseForm(initial=initial_data)

    try:
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')
        df = yf.download(f'{kod}', start='2010-01-01', end=end_date)

        if df.empty:
            context[
                'hata'] = 'Veri alınamadı veya geçersiz hisse kodu. Lütfen doğru bir hisse kodu girdiğinizden emin olun.'
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.columns = [col.capitalize() for col in df.columns]

            if 'Close' not in df.columns or 'High' not in df.columns or 'Low' not in df.columns or 'Volume' not in df.columns:
                context[
                    'hata'] = "Hisse senedi verilerinde gerekli sütunlar (Close, High, Low, Volume) bulunamadı. Analiz yapılamıyor."
                return render(request, 'analiz/analiz.html', context)

            close_prices = df['Close']
            high_prices = df['High']
            low_prices = df['Low']
            volume_data = df['Volume']

            df['SMA_20'] = SMAIndicator(close=close_prices, window=20).sma_indicator()
            df['EMA_50'] = EMAIndicator(close=close_prices, window=50).ema_indicator()
            df['EMA_200'] = EMAIndicator(close=close_prices, window=200).ema_indicator()
            df['Volume_SMA_20'] = volume_data.rolling(window=20).mean()

            bollinger = BollingerBands(close=close_prices, window=20, window_dev=2)
            df['BB_High'] = bollinger.bollinger_hband()
            df['BB_Low'] = bollinger.bollinger_lband()
            df['BB_Mid'] = bollinger.bollinger_mavg()
            df['ATR'] = AverageTrueRange(high=high_prices, low=low_prices, close=close_prices,
                                         window=14).average_true_range()

            df['RSI'] = RSIIndicator(close=close_prices, window=14).rsi()
            macd = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Hist'] = macd.macd_diff()
            df['StochRSI'] = stochrsi(close=close_prices, window=14, smooth1=3, smooth2=3)
            df['ROC'] = ROCIndicator(close=close_prices, window=12).roc()

            df['ADX'] = ADXIndicator(high=high_prices, low=low_prices, close=close_prices, window=14).adx()
            df['ADX_Pos'] = ADXIndicator(high=high_prices, low=low_prices, close=close_prices, window=14).adx_pos()
            df['ADX_Neg'] = ADXIndicator(high=high_prices, low=low_prices, close=close_prices, window=14).adx_neg()

            df['CCI'] = CCIIndicator(high=high_prices, low=low_prices, close=close_prices, window=20).cci()

            df['OBV'] = OnBalanceVolumeIndicator(close=close_prices, volume=volume_data).on_balance_volume()

            df = df.dropna()

            if df.empty:
                context[
                    'hata'] = 'Hesaplama için yeterli veri bulunamadı. Lütfen farklı bir hisse kodu veya tarih aralığı deneyin.'
            else:
                bugun = df.iloc[-1]
                bugun_onceki = df.iloc[-2] if len(df) > 1 else None

                bugunku_fiyat = get_scalar_value(bugun['Close'])

                if baslangic_tarihi:
                    start_date_dt = datetime.datetime.combine(baslangic_tarihi, datetime.time.min)

                    eski_fiyat = None
                    actual_start_date = None

                    available_dates = df.index[df.index >= start_date_dt]
                    if not available_dates.empty:
                        actual_start_date = available_dates[0]
                        eski_fiyat = get_scalar_value(df.loc[actual_start_date]['Close'])
                        if actual_start_date.date() != baslangic_tarihi:
                            getiriyazisi = (
                                f"Seçilen başlangıç tarihi olan {baslangic_tarihi.strftime('%d.%m.%Y')} için işlem verisi bulunamadığından, "
                                f"en yakın işlem günü olan {actual_start_date.strftime('%d.%m.%Y')} baz alınmıştır. "
                            )
                        else:
                            getiriyazisi = ""

                    if eski_fiyat is not None and bugunku_fiyat is not None:
                        fark = bugunku_fiyat - eski_fiyat
                        yuzde = (fark / eski_fiyat) * 100 if eski_fiyat != 0 else 0

                        if fark > 0:
                            durum = 'kar'
                            fark_metin = f"{abs(fark):.2f} ₺ artış"
                        elif fark < 0:
                            durum = 'zarar'
                            fark_metin = f"{abs(fark):.2f} ₺ düşüş"
                        else:
                            durum = 'değişim olmamıştır'
                            fark_metin = "değişim olmamıştır"
                        getiriyazisi += (
                            f"Bu hisseye yapılan yatırımda, bugünkü kapanış fiyatı olan {bugunku_fiyat:.2f} ₺'ye göre %{yuzde:.2f} oranında bir {durum} söz konusu olmuştur. "
                            f"Bu, başlangıç fiyatı olan {eski_fiyat:.2f} ₺'den bugünkü kapanış fiyatı olan {bugunku_fiyat:.2f} ₺'ye {fark_metin} anlamına gelmektedir."
                        )
                    else:
                        getiriyazisi = (
                            f"Seçtiğiniz başlangıç tarihi olan {baslangic_tarihi.strftime('%d.%m.%Y')} ve sonrasında işlem verisi bulunamadı veya bugünkü fiyat bilgisi eksik. "
                            "Lütfen geçerli bir tarih seçtiğinizden emin olun."
                        )
                else:
                    getiriyazisi = (
                        "Başlangıç tarihi belirtilmediği için belirli bir dönemdeki getiri analizi yapılamamıştır. "
                        "Ancak hissenin mevcut durumu aşağıda detaylıca yorumlanmıştır."
                    )

                context['kod'] = kod
                context['getiri_yorumu'] = getiriyazisi

                fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.05,
                                    row_heights=[0.5, 0.25, 0.25])

                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Mum Grafiği'
                ), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='SMA 20'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], mode='lines', name='EMA 50'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], mode='lines', name='EMA 200'), row=1, col=1)
                fig.add_trace(
                    go.Scatter(x=df.index, y=df['BB_High'], mode='lines', name='BB Üst', line=dict(dash='dash')), row=1,
                    col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Mid'], mode='lines', name='BB Orta'), row=1, col=1)
                fig.add_trace(
                    go.Scatter(x=df.index, y=df['BB_Low'], mode='lines', name='BB Alt', line=dict(dash='dash')), row=1,
                    col=1)

                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI'), row=2, col=1)
                fig.add_hline(y=70, line_dash='dot', annotation_text='Aşırı Alım (70)', row=2, col=1)
                fig.add_hline(y=30, line_dash='dot', annotation_text='Aşırı Satım (30)', row=2, col=1)

                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', name='MACD Sinyal'), row=3,
                              col=1)
                fig.add_trace(go.Bar(
                    x=df.index, y=df['MACD_Hist'], name='MACD Histogram',
                    marker_color=['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                ), row=3, col=1)
                fig.add_hline(y=0, line_dash='dot', row=3, col=1)

                fig.update_layout(
                    title_text=f'{kod} Hisse Senedi Analizi',
                    xaxis_rangeslider_visible=False,
                    height=800,
                    hovermode='x unified',
                    template='plotly_white'
                )
                fig.update_yaxes(title_text='Fiyat', row=1, col=1)
                fig.update_yaxes(title_text='RSI', row=2, col=1)
                fig.update_yaxes(title_text='MACD', row=3, col=1)
                context['grafik'] = fig.to_json()

                rsi_deger = get_scalar_value(bugun['RSI'])
                if rsi_deger is not None:
                    if rsi_deger >= 70:
                        rsi_status = "aşırı alım bölgesinde"
                        rsi_implication = "bir düzeltme veya düşüş potansiyelinin artabileceğine"
                        rsi_trend_note = "Ancak, güçlü trendlerde RSI'nın uzun süre aşırı alım bölgesinde kalabileceği unutulmamalıdır."
                    elif rsi_deger <= 30:
                        rsi_status = "aşırı satım bölgesinde"
                        rsi_implication = "bir tepki yükselişinin veya toparlanmanın görülebileceğine"
                        rsi_trend_note = "Ancak, düşüş trendlerinde RSI'nın uzun süre aşırı satım bölgesinde kalabileceği de göz önünde bulundurulmalıdır."
                    else:
                        rsi_status = "nötr bölgede"
                        rsi_implication = "şu an için aşırı alım veya satım koşullarında olmadığını, ancak belirsiz bir konsolidasyon sürecinde olabileceğini"
                        rsi_trend_note = "Bu durumda, yatırımcıların yön tayini için diğer teknik göstergelerle birlikte değerlendirme yapması önemlidir."

                    context['rsi_yorum'] = (
                            f"Göreceli Güç Endeksi (RSI) değeri {rsi_deger:.2f} seviyesinde olup, hissenin {rsi_status} olduğunu göstermektedir. "
                            f"Bu durum, hissede bir {rsi_implication} işaret edebilir. "
                            + rsi_trend_note
                    )
                else:
                    context['rsi_yorum'] = "RSI verisi bulunamadı veya hesaplanamadı."

                cci_deger = get_scalar_value(bugun['CCI'])
                if cci_deger is not None:
                    if cci_deger > 100:
                        cci_region = "+100'ün üzerinde"
                        cci_action = "aşırı alım bölgesine girdiğini ve bir yükseliş trendi içerisinde güçlü bir yukarı yönlü momentum sergilediğini"
                        cci_followup = "Bu seviyelerden bir düzeltme gelebileceği de göz önünde bulundurulmalıdır."
                    elif cci_deger < -100:
                        cci_region = "-100'ün altında"
                        cci_action = "aşırı satım bölgesine girdiğini ve bir düşüş trendi içerisinde güçlü bir aşağı yönlü momentum sergilediğini"
                        cci_followup = "Bu seviyelerden bir tepki yükselişi gelebileceği de göz önünde bulundurulmalıdır."
                    else:
                        cci_region = "nötr bölgede"
                        cci_action = "belirgin bir aşırı alım veya satım koşulu olmadığını, dolayısıyla güçlü bir alım ya da satım sinyali bulunmadığını"
                        cci_followup = "Piyasa kararsız bir seyir izleyebilir."

                    context['cci_yorum'] = (
                        f"Emtia Kanal Endeksi (CCI) değeri {cci_deger:.2f} seviyesi ile {cci_region} seyrediyor. "
                        f"Bu durum, hissenin {cci_action} göstermektedir. {cci_followup}"
                    )
                else:
                    context['cci_yorum'] = "CCI verisi bulunamadı veya hesaplanamadı."

                stochrsi_deger = get_scalar_value(bugun['StochRSI'])
                if stochrsi_deger is not None:
                    if stochrsi_deger >= 80:
                        stoch_region = "aşırı alım bölgesinde"
                        stoch_action = "geri çekilme veya düşüş potansiyelinin arttığını"
                        stoch_followup = "Ancak, güçlü yükseliş trendlerinde bu gösterge uzun süre aşırı alım bölgesinde kalabilir."
                    elif stochrsi_deger <= 20:
                        stoch_region = "aşırı satım bölgesinde"
                        stoch_action = "tepki yükselişinin veya toparlanmanın görülebileceğine"
                        stoch_followup = "Ancak, düşüş trendlerinde bu gösterge uzun süre aşırı satım bölgesinde kalabileceği de göz önünde bulundurulmalıdır."
                    else:
                        stoch_region = "orta bölgede"
                        stoch_action = "net bir aşırı alım veya satım koşulunda olmadığını"
                        stoch_followup = "Bu gösterge, yön tayini için diğer göstergelerle birlikte kullanılmalı ve güçlü trendlerde daha az güvenilir olabileceği unutulmamalıdır."

                    context['stochrsi_yorum'] = (
                        f"Stochastic RSI göstergesi {stochrsi_deger:.2f} seviyesinde olup, {stoch_region} bulunuyor. "
                        f"Bu, hissede kısa vadede bir {stoch_action} gösterebilir. {stoch_followup}"
                    )
                else:
                    context['stochrsi_yorum'] = "Stochastic RSI verisi bulunamadı veya hesaplanamadı."

                macd_deger = get_scalar_value(bugun['MACD'])
                macd_signal_deger = get_scalar_value(bugun['MACD_Signal'])
                macd_hist_deger = get_scalar_value(bugun['MACD_Hist'])

                if None not in [macd_deger, macd_signal_deger, macd_hist_deger]:
                    macd_yorum = f"Hareketli Ortalama Yakınsama Iraksama (MACD) göstergesi (MACD: {macd_deger:.2f}, Sinyal: {macd_signal_deger:.2f}) şu anki durumda "

                    prev_macd_hist_deger = None
                    if bugun_onceki is not None and 'MACD_Hist' in bugun_onceki:
                        prev_macd_hist_deger = get_scalar_value(bugun_onceki['MACD_Hist'])

                    if macd_deger > macd_signal_deger:
                        macd_yorum += "MACD çizgisi sinyal çizgisinin üzerinde seyrederek güçlü bir yukarı yönlü momentumu ve potansiyel alım sinyalini işaret etmektedir. "
                        if prev_macd_hist_deger is not None and macd_hist_deger > 0 and macd_hist_deger > prev_macd_hist_deger:
                            macd_yorum += "Histogram değerleri de pozitif ve yükselişte olup, yükseliş trendinin güçlendiğini göstermektedir."
                        elif macd_hist_deger > 0:
                            macd_yorum += "Histogram değerleri pozitif seyretmekte, ancak momentumda yavaşlama olabilir."
                        else:
                            macd_yorum += "Histogram negatiften pozitife dönmeye çalışıyor, bu da bir dönüş sinyali olabilir."
                    elif macd_deger < macd_signal_deger:
                        macd_yorum += "MACD çizgisi sinyal çizgisinin altında seyrederek potansiyel bir satış sinyalini ve aşağı yönlü momentumu göstermektedir. "
                        if prev_macd_hist_deger is not None and macd_hist_deger < 0 and macd_hist_deger < prev_macd_hist_deger:
                            macd_yorum += "Histogram değerleri de negatif ve düşüşte olup, düşüş trendinin güçlendiğini göstermektedir."
                        elif macd_hist_deger < 0:
                            macd_yorum += "Histogram değerleri negatif seyretmekte, ancak momentumda yavaşlama olabilir."
                        else:
                            macd_yorum += "Histogram pozitiften negatife dönmeye çalışıyor, bu da bir düşüş sinyali olabilir."
                    else:
                        macd_yorum += "MACD çizgisi sinyal çizgisi ile kesişim noktasında veya çok yakınında olup, kararsız bir piyasa veya trend dönüşü sinyali vermektedir. "
                        macd_yorum += "Histogram sıfır çizgisi etrafında dalgalanarak belirsizliği vurgulamaktadır."

                    context['macd_yorum'] = macd_yorum
                else:
                    context['macd_yorum'] = "MACD verisi bulunamadı veya hesaplanamadı."

                bb_high = get_scalar_value(bugun['BB_High'])
                bb_low = get_scalar_value(bugun['BB_Low'])
                bb_mid = get_scalar_value(bugun['BB_Mid'])

                if None not in [bb_high, bb_low, bb_mid, bugunku_fiyat]:
                    bb_yorum = f"Bollinger Bantları'na göre (Üst Bant: {bb_high:.2f}, Orta Bant (SMA 20): {bb_mid:.2f}, Alt Bant: {bb_low:.2f}), "
                    if bugunku_fiyat > bb_high:
                        bb_yorum += "hissenin fiyatı üst bandın üzerine çıkarak aşırı alım bölgesine girdiğini veya güçlü bir yükseliş trendi içerisinde olduğunu göstermektedir. Bu durum genellikle bir geri çekilme veya düzeltme beklentisini artırır, ancak güçlü trendlerde fiyatlar bir süre üst bant üzerinde kalabilir."
                    elif bugunku_fiyat < bb_low:
                        bb_yorum += "hissenin fiyatı alt bandın altına inerek aşırı satım bölgesine girdiğini veya güçlü bir düşüş trendi içerisinde olduğunu göstermektedir. Bu durum genellikle bir tepki yükselişi veya toparlanma beklentisini artırır, ancak güçlü düşüş trendlerinde fiyatlar bir süre alt bant altında kalabilir."
                    elif bugunku_fiyat > bb_mid:
                        bb_yorum += "hissenin fiyatı orta bandın (20 günlük Basit Hareketli Ortalama) üzerinde seyrederek orta vadeli bir yükseliş eğilimi olduğunu göstermektedir. Orta bant önemli bir destek seviyesi olarak işlev görebilir."
                    elif bugunku_fiyat < bb_mid:
                        bb_yorum += "hissenin fiyatı orta bandın (20 günlük Basit Hareketli Ortalama) altında seyrederek orta vadeli bir düşüş eğilimi olduğunu göstermektedir. Orta bant önemli bir direnç seviyesi olarak işlev görebilir."
                    else:
                        bb_yorum += "hissenin fiyatı orta banda yakın seyrederek piyasanın konsolidasyon veya kararsızlık içinde olduğunu göstermektedir. Bantların daralması potansiyel bir volatilite artışına işaret edebilirken, genişlemesi mevcut trendin gücünü yansıtır."

                    context['bollinger_yorum'] = bb_yorum
                else:
                    context['bollinger_yorum'] = "Bollinger Bantları verisi bulunamadı veya hesaplanamadı."

                adx_deger = get_scalar_value(bugun['ADX'])
                plus_di_deger = get_scalar_value(bugun['ADX_Pos'])
                minus_di_deger = get_scalar_value(bugun['ADX_Neg'])

                if None not in [adx_deger, plus_di_deger, minus_di_deger]:
                    adx_yorum = f"Ortalama Yönsel Endeks (ADX) değeri {adx_deger:.2f} seviyesindedir. "

                    if adx_deger < 20:
                        adx_yorum += "Bu seviye, hissede zayıf veya belirsiz bir trend olduğunu, yani piyasanın konsolidasyon veya yatay bir seyir izlediğini göstermektedir. Güçlü bir yönsel hareket beklenmeyebilir."
                    elif 20 <= adx_deger < 40:
                        adx_yorum += "Bu seviye, hissede orta güçte bir trend olduğunu göstermektedir. Yükseliş veya düşüş trendi henüz çok güçlü olmasa da belirgin bir yön bulunmaktadır. (ADX, trendin yönünü değil, sadece gücünü gösterir.)"
                    elif 40 <= adx_deger < 60:
                        adx_yorum += "Bu seviye, hissede güçlü bir trend olduğunu göstermektedir. Mevcut trendin (yükseliş veya düşüş) oldukça kararlı ve sağlam olduğunu belirtir. Trendin devam etme olasılığı yüksektir."
                    else:
                        adx_yorum += "Bu seviye, hissede çok güçlü bir trend olduğunu göstermektedir. Mevcut trendin oldukça kuvvetli ve yerleşik olduğunu belirtir. Aşırı güçlü trendler bazen bir tükenme veya düzeltme öncesi son bir ivme de olabilir."

                    adx_yorum += f" Bugünkü +DI ({plus_di_deger:.2f}) ve -DI ({minus_di_deger:.2f}) değerlerine bakıldığında, "
                    if plus_di_deger > minus_di_deger:
                        adx_yorum += "yükseliş yönlü bir trendin baskın olduğu düşünülmektedir. (+DI'nın -DI'dan yüksek olması yükseliş eğilimini destekler.)"
                    elif minus_di_deger > plus_di_deger:
                        adx_yorum += "düşüş yönlü bir trendin baskın olduğu düşünülmektedir. (-DI'nın +DI'dan yüksek olması düşüş eğilimini destekler.)"
                    else:
                        adx_yorum += "yön konusunda belirsizlik bulunmaktadır."

                    context['adx_yorum'] = adx_yorum
                else:
                    context['adx_yorum'] = "ADX verisi bulunamadı veya hesaplanamadı."

                roc_deger = get_scalar_value(bugun['ROC'])
                if roc_deger is not None:
                    roc_yorum = f"Fiyat Değişim Oranı (ROC) göstergesi {roc_deger:.2f} seviyesindedir. "
                    prev_roc_deger = None
                    if bugun_onceki is not None and 'ROC' in bugun_onceki:
                        prev_roc_deger = get_scalar_value(bugun_onceki['ROC'])

                    if roc_deger > 0:
                        roc_yorum += "ROC pozitif bölgede seyretmektedir, bu da hisse fiyatının son 12 dönemde (varsayılan) yükseliş gösterdiğini ve yukarı yönlü bir momentum olduğunu işaret eder. "
                        if prev_roc_deger is not None:
                            if roc_deger > prev_roc_deger:
                                roc_yorum += "Momentum artıyor."
                            elif roc_deger < prev_roc_deger:
                                roc_yorum += "Momentumda yavaşlama var."
                    elif roc_deger < 0:
                        roc_yorum += "ROC negatif bölgede seyretmektedir, bu da hisse fiyatının son 12 dönemde düşüş gösterdiğini ve aşağı yönlü bir momentum olduğunu işaret eder. "
                        if prev_roc_deger is not None:
                            if roc_deger < prev_roc_deger:
                                roc_yorum += "Düşüş momentumu artıyor."
                            elif roc_deger > prev_roc_deger:
                                roc_yorum += "Düşüş momentumunda yavaşlama var."
                    else:
                        roc_yorum += "ROC sıfır seviyesine yakın seyretmektedir, bu da hisse fiyatının son 12 dönemde kayda değer bir değişiklik göstermediğini ve piyasanın konsolidasyon veya kararsızlık içinde olduğunu işaret eder."

                    context['roc_yorum'] = roc_yorum
                else:
                    context['roc_yorum'] = "ROC verisi bulunamadı veya hesaplanamadı."

                atr_deger = get_scalar_value(bugun['ATR'])
                if atr_deger is not None:
                    atr_yorum = f"Ortalama Gerçek Aralık (ATR) değeri {atr_deger:.2f} seviyesindedir. "
                    if len(df) > 20 and 'ATR' in df.columns:
                        avg_atr = df['ATR'].iloc[-20:-1].mean()
                        if pd.notna(avg_atr):
                            if atr_deger > avg_atr * 1.2:
                                atr_yorum += "Bu seviye, son dönemde volatilitenin (fiyat oynaklığının) önemli ölçüde arttığını göstermektedir. Yüksek ATR, daha büyük fiyat hareketleri ve dolayısıyla daha yüksek risk anlamına gelebilir. Trendlerin ivmelendiği veya büyük haberlerin olduğu dönemlerde ATR yükselir."
                            elif atr_deger < avg_atr * 0.8:
                                atr_yorum += "Bu seviye, son dönemde volatilitenin (fiyat oynaklığının) önemli ölçüde azaldığını göstermektedir. Düşük ATR, daha küçük fiyat hareketleri ve konsolidasyon dönemlerine işaret edebilir. Volatilitenin azalması, genellikle büyük bir hareket öncesinde görülebilir."
                            else:
                                atr_yorum += "Bu seviye, hissenin orta düzeyde bir volatilite sergilediğini göstermektedir. Fiyat hareketleri normal aralıklarda seyretmektedir."
                        else:
                            atr_yorum += "Yeterli geçmiş ATR verisi bulunmadığı için volatilite karşılaştırması yapılamamıştır."
                    else:
                        atr_yorum += "Bu seviye, hissenin mevcut volatilite düzeyini yansıtmaktadır. Yüksek değerler daha fazla oynaklık, düşük değerler ise daha az oynaklık anlamına gelir."

                    atr_yorum += " ATR, özellikle stop-loss ve kar al hedeflerini belirlemede yatırımcılara yardımcı olabilir."
                    context['atr_yorum'] = atr_yorum
                else:
                    context['atr_yorum'] = "ATR verisi bulunamadı veya hesaplanamadı."

                obv_deger = get_scalar_value(bugun['OBV'])
                if obv_deger is not None:
                    prev_obv_deger = None
                    if bugun_onceki is not None and 'OBV' in bugun_onceki:
                        prev_obv_deger = get_scalar_value(bugun_onceki['OBV'])

                    obv_yorum = f"Denge Hacmi (OBV) göstergesi {obv_deger:.2f} seviyesindedir. "

                    if prev_obv_deger is not None:
                        if obv_deger > prev_obv_deger:
                            obv_yorum += "OBV değeri bir önceki güne göre yükselmiş olup, alıcı hacminin satıcı hacminden daha fazla olduğunu ve bir birikim (alıcı ilgisi) olduğunu göstermektedir. Bu, genellikle fiyatların da yükselme potansiyeline sahip olduğunu veya mevcut yükseliş trendinin desteklendiğini işaret eder."
                        elif obv_deger < prev_obv_deger:
                            obv_yorum += "OBV değeri bir önceki güne göre düşmüş olup, satıcı hacminin alıcı hacminden daha fazla olduğunu ve bir dağıtım (satıcı baskısı) olduğunu göstermektedir. Bu, genellikle fiyatların da düşme potansiyeline sahip olduğunu veya mevcut düşüş trendinin desteklendiğini işaret eder."
                        else:
                            obv_yorum += "OBV değeri bir önceki güne göre değişmemiş olup, hacimde net bir alıcı veya satıcı baskısı olmadığını ve piyasanın kararsız bir dengeye ulaştığını göstermektedir."
                    else:
                        obv_yorum += "Geçmiş OBV verisi olmadığı için önceki günle karşılaştırma yapılamamıştır."

                    if bugun_onceki is not None and 'Close' in bugun_onceki:
                        prev_close = get_scalar_value(bugun_onceki['Close'])
                        if prev_close is not None and bugunku_fiyat is not None and prev_obv_deger is not None:
                            if bugunku_fiyat > prev_close and obv_deger < prev_obv_deger:
                                obv_yorum += " Negatif Uyumsuzluk (Bearish Divergence): Fiyat yükselirken OBV düşüyor. Bu, yükselişin hacim tarafından desteklenmediğini ve bir düzeltme gelebileceğini gösteren zayıf bir sinyal olabilir."
                            elif bugunku_fiyat < prev_close and obv_deger > prev_obv_deger:
                                obv_yorum += " Pozitif Uyumsuzluk (Bullish Divergence): Fiyat düşerken OBV yükseliyor. Bu, düşüşün hacim tarafından desteklenmediğini ve bir toparlanma gelebileceğini gösteren güçlü bir sinyal olabilir."

                    context['obv_yorum'] = obv_yorum
                else:
                    context['obv_yorum'] = "OBV verisi bulunamadı veya hesaplanamadı."

    except Exception as e:
        traceback.print_exc()
        context[
            'hata'] = f'Veri alımında veya analizde bir hata oluştu: {str(e)}. Lütfen hisse kodunu kontrol edin veya daha sonra tekrar deneyin.'

    context['form'] = form
    return render(request, 'analiz/analiz.html', context)