import numpy as np
import plotly.graph_objects as go
import math

def dbm_to_mv(dbm, r=50):
    """
    将 dBm 转换为 mV（峰峰值未计算，这里返回的是有效值 RMS）
    :param dbm: 输入功率，单位 dBm
    :param r: 负载电阻，默认 50Ω
    :return: 电压，单位 mV (RMS)
    """
    # 1. dBm 转 mW
    mw = 10 ** (dbm / 10)
    # 2. mW 转 W
    watt = mw / 1000
    # 3. 功率转电压 Vrms
    vrms = math.sqrt(watt * r)
    # 4. 转为 mV
    mv = vrms * 1000
    return mv

def analyze_iq_signal(
    Idata, Qdata,
    fs=24e6, vpp=1.1, nbit=12, R=50,sg_pwr=-70,
    integ_bins=10, DC_bins=10, dump_noise =0,figure_off=1,
    target_tone_freq=1e6, target_tone_search_span=0.2e6,
    noise_integ_start_freq=0.5e6, noise_integ_stop_freq=1.5e6,
    chn=None, ble_mode=None
):

    # ========== IQ 数据输入 ==========
    Idata_dec = np.array(Idata)
    Qdata_dec = np.array(Qdata)

    # ========== 电压转换 ==========
    Idata_volt = Idata_dec / (2**(nbit - 1) - 1) * vpp / 2
    Qdata_volt = Qdata_dec / (2**(nbit - 1) - 1) * vpp / 2
    complex_signal = Idata_volt + 1j * Qdata_volt

    # ========== 加窗和 FFT ==========
    window = np.hanning(len(complex_signal))
    signal_windowed = complex_signal * window
    n = len(signal_windowed)
    rbw = fs / n  # 分辨率带宽（Hz）
    fft_result = np.fft.fftshift(np.fft.fft(signal_windowed, n))
    freqs_Hz = np.fft.fftshift(np.fft.fftfreq(n, d=1/fs))

    # ========== PSD 转功率计算 ==========
    psd_voltsq = (1 / (fs * np.sum(window**2))) * np.abs(fft_result)**2
    psd_watts = psd_voltsq / R *rbw # W/Hz 转成 W
    power_dBm = 10 * np.log10(psd_watts + 1e-20) + 30 #转换成 dBmW

    # ========== 提取单音信号搜索范围 ==========
    tone_search_mask = (freqs_Hz >= target_tone_freq - target_tone_search_span) & (freqs_Hz <= target_tone_freq + target_tone_search_span)
    search_freqs = freqs_Hz[tone_search_mask]
    search_power_dBm = power_dBm[tone_search_mask]

    # ========== 找峰值 ==========
    peak_idx = np.argmax(search_power_dBm)
    peak_power = search_power_dBm[peak_idx]

    # 获取峰值在原始数组中的索引
    search_indices = np.where(tone_search_mask)[0]
    peak_idx_in_all_freqs = search_indices[peak_idx]

    # ========= 左右积分bins ========
    # left_idx = peak_idx_in_all_freqs - integ_bins
    # right_idx = peak_idx_in_all_freqs + integ_bins
    left_idx = max(0, peak_idx_in_all_freqs - integ_bins)
    right_idx = min(n - 1, peak_idx_in_all_freqs + integ_bins)


    # ========== 信号功率（直接求和积分） ==========
    bw_Hz = (right_idx - left_idx) * rbw
    signal_power_linear = np.sum(psd_watts[left_idx:right_idx])
    signal_power_dBm = 10 * np.log10(signal_power_linear + 1e-20) + 30

    # ========== DC功率（直接求和积分） ==========
    # 找到最接近0的频率索引
    DC_idx = np.argmin(np.abs(freqs_Hz))

    # 确保索引在有效范围内
    dc_left_idx = max(0, DC_idx - DC_bins)
    dc_right_idx = min(len(freqs_Hz) - 1, DC_idx + DC_bins)

    # 计算直流功率
    DC_power_linear = np.sum(psd_watts[dc_left_idx:dc_right_idx])
    DC_power_dBm = 10 * np.log10(DC_power_linear + 1e-20) + 30

    DC_mV = dbm_to_mv(DC_power_dBm)

    # ========== 信号镜像功率（直接求和积分） ==========
    image_integ_right = DC_idx*2 - left_idx
    image_integ_left = DC_idx*2 - right_idx
    image_power_linear = np.sum(psd_watts[image_integ_left:image_integ_right])
    image_power_dBm = 10 * np.log10(image_power_linear + 1e-20) + 30

    # 计算Noise功率
    noise_integ_freq_mask = (freqs_Hz >= noise_integ_start_freq) & (freqs_Hz <= noise_integ_stop_freq)
    # 获取Noise积分区间在原始数组中的索引
    noise_indices = np.where(noise_integ_freq_mask)[0]
    noise_integ_left = noise_indices[0]
    noise_integ_right = noise_indices[-1]
    noise_power_linear = np.sum(psd_watts[noise_integ_freq_mask])
    noise_power_dBm = 10 * np.log10(noise_power_linear + 1e-20) + 30

    # ========== SNR & IMRR ==========
    SNR_dB = signal_power_dBm - noise_power_dBm
    IMRR_dB = signal_power_dBm - image_power_dBm

    # ========== 可视化 ==========

    #创建一个新的 Plotly 图形 - 时域 I、Q 信号
    SN = len(Idata_volt)
    t = np.arange(SN) / fs * 1e6  # 转换为微秒
    fig_time_domain = go.Figure()
    fig_time_domain.add_trace(go.Scatter(x=t, y=Idata_volt, name='I Component'))
    fig_time_domain.add_trace(go.Scatter(x=t, y=Qdata_volt, name='Q Component'))
    fig_time_domain.update_layout(
        title='Time Domain I and Q Components of Signal',
        xaxis_title='Time (μs)',
        yaxis_title='Amplitude (V)',
        height=600,
        margin=dict(l=80, r=20, t=80, b=100),  # 增加底部边距以显示x轴
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            showticklabels=True,
            tickmode='auto'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linecolor='black',
            showticklabels=True,
            tickmode='auto'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    if(figure_off == 0):
        fig = go.Figure()
    
        # 全频谱（黑色折线）
        fig.add_trace(go.Scatter(
            x=freqs_Hz / 1e6,  # 统一单位为MHz（避免科学计数法）
            y=power_dBm,
            mode='lines',
            name='Power Spectrum',
            line=dict(color='black', width=1)
        ))
    
    
        # 峰值标注（悬浮在上方）
        fig.add_trace(go.Scatter(
            x=[search_freqs[peak_idx] / 1e6],
            y=[peak_power], 
            mode='markers+text',
            name='Peak',
            marker=dict(color='red', size=10),
            text=[f"Peak: {peak_power:.2f} dBm"],
            textposition="top center",
            hoverinfo='none'
        ))
    
        # 标记Noise积分区间
        fig.add_vrect(
            x0=freqs_Hz[noise_integ_left] / 1e6,
            x1=freqs_Hz[noise_integ_right] / 1e6,
            fillcolor='gray',
            opacity=0.2,
            line_width=0
        )
    
        # 信号频段区域（浅绿色填充）
        fig.add_vrect(
            x0=freqs_Hz[left_idx] / 1e6,
            x1=freqs_Hz[right_idx] / 1e6,
            fillcolor='lightgreen', 
            opacity=0.2,
            line_width=0,
            annotation_text=f"积分带宽 (BW={bw_Hz/1e6:.2f} MHz)",  # 标注带宽
            annotation_position="top left",  # 标注移到左上角
            annotation_font_size=12
        )
    
        # 标记信号镜像积分区间
        fig.add_vrect(
            x0=freqs_Hz[image_integ_left] / 1e6,
            x1=freqs_Hz[image_integ_right] / 1e6,
            fillcolor='lightgreen',
            opacity=0.2,
            line_width=0
        )
    
        # 构建标题文本
        title_text = 'Power Spectrum'
        if chn is not None and ble_mode is not None:
            freq_mhz = 2400 + chn * 2
            title_text = f'Power Spectrum - Chn:{freq_mhz}MHz ({ble_mode})'
        elif chn is not None:
            freq_mhz = 2400 + chn * 2
            title_text = f'Power Spectrum - Chn:{freq_mhz}MHz'

        # 图表布局优化
        fig.update_layout(
            title=dict(
                text=f'{title_text}<br>'
                    f'<span style="font-size: 12px;"> DC Power: {DC_mV:.2f} mV | Signal Power: {signal_power_dBm:.2f} dBm | '
                    f'Image Power: {image_power_dBm:.2f} dBm | IMRR:{IMRR_dB:.2f} dBm | '
                    f'Noise: {noise_power_dBm:.2f} dBm | SNR: {SNR_dB:.2f} dB | Gain: {round(signal_power_dBm - sg_pwr,2)} dB</span>',
                x=0.05,  # 标题左对齐
                xanchor='left'
            ),
            xaxis_title='Frequency (MHz)',
            yaxis_title='Power (dBm)',
            plot_bgcolor='white', #背景色
            paper_bgcolor='white',
            height=600,
            margin=dict(l=80, r=20, t=80, b=100),  # 增加底部边距以显示x轴
            xaxis=dict(
                showgrid=True,
                gridcolor='lightgray',
                showline=True,
                linecolor='black',
                showticklabels=True,
                tickmode='auto',
                range=[freqs_Hz.min()/1e6, freqs_Hz.max()/1e6]  # 强制撑满横轴
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='lightgray',
                showline=True,
                linecolor='black',
                showticklabels=True,
                tickmode='auto',
                range=[-110, 10]  # 固定纵轴范围
            ),
            legend=dict(
                x=0.99,  # 图例移到右上角
                y=0.99,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.5)'
            ),
            hovermode='x unified'
        )
        
        # 返回图表对象而不是直接显示
        result = {
            "noise": None,
            "signal": None,
            "gain": None,
            "dc": None,
            "image": None,
            "snr": None,
            "imrr": None,
            "time_chart": fig_time_domain,
            "freq_chart": fig
        }

        if dump_noise:  # 只更新 noise
            result["noise"] = round(noise_power_dBm, 4)
        else:  # 只更新 tone 相关指标
            result.update({
                "signal": round(signal_power_dBm, 4),
                "gain": round(signal_power_dBm - sg_pwr,4),
                "dc": round(DC_mV, 4),
                "image": round(image_power_dBm, 4),
                "snr": round(SNR_dB, 4),
                "imrr": round(IMRR_dB, 4)
            })

        return result

    # 统一返回结构（不显示图表时）
    result = {
        "noise": None,
        "signal": None,
        "gain": None,
        "dc": None,
        "image": None,
        "snr": None,
        "imrr": None
    }

    if dump_noise:  # 只更新 noise
        result["noise"] = round(noise_power_dBm, 4)
    else:  # 只更新 tone 相关指标
        result.update({
            "signal": round(signal_power_dBm, 4),
            "gain": round(signal_power_dBm - sg_pwr,4),
            "dc": round(DC_mV, 4),
            "image": round(image_power_dBm, 4),
            "snr": round(SNR_dB, 4),
            "imrr": round(IMRR_dB, 4)
        })

    return result
