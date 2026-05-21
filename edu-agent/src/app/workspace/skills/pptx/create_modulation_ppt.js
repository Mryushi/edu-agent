const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FaSignal, FaWaveSquare, FaExchangeAlt, FaChartLine,
  FaMicrochip, FaProjectDiagram, FaCheckCircle, FaArrowRight,
  FaBookOpen, FaCogs, FaChartBar, FaRocket
} = require("react-icons/fa");

function renderIconSvg(IconComponent, color = "#000000", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}

async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

// Color palette - Ocean Gradient (通信主题)
const C = {
  darkBg: "065A82",      // 深蓝
  teal: "1C7293",        // 青色
  midnight: "21295C",    // 午夜蓝
  accent: "02C39A",      // 薄荷绿
  light: "E8F4F8",       // 浅蓝背景
  white: "FFFFFF",
  offWhite: "F0F7FA",
  textDark: "1A2332",
  textMuted: "5A6B7F",
  cardBg: "FFFFFF",
  highlight: "FFD166",   // 暖黄高亮
};

const FONT_TITLE = "Georgia";
const FONT_BODY = "Calibri";

// Helper: fresh shadow factory
const cardShadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.10 });

async function createPresentation() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "yue - 通信工程";
  pres.title = "模拟调制与解调";

  // Pre-render icons
  const icons = {};
  const iconList = [
    ["signal", FaSignal, C.white],
    ["wave", FaWaveSquare, C.white],
    ["exchange", FaExchangeAlt, C.white],
    ["chart", FaChartLine, C.white],
    ["chip", FaMicrochip, C.white],
    ["project", FaProjectDiagram, C.white],
    ["check", FaCheckCircle, C.accent],
    ["arrow", FaArrowRight, C.teal],
    ["book", FaBookOpen, C.white],
    ["cogs", FaCogs, C.white],
    ["chartBar", FaChartBar, C.white],
    ["rocket", FaRocket, C.white],
    ["signalDark", FaSignal, C.teal],
    ["waveDark", FaWaveSquare, C.teal],
    ["exchangeDark", FaExchangeAlt, C.teal],
    ["checkDark", FaCheckCircle, C.accent],
    ["cogsDark", FaCogs, C.teal],
    ["chartDark", FaChartLine, C.teal],
    ["chipDark", FaMicrochip, C.teal],
    ["bookDark", FaBookOpen, C.teal],
  ];
  for (const [name, comp, color] of iconList) {
    icons[name] = await iconToBase64Png(comp, "#" + color, 256);
  }

  // ============ SLIDE 1: 封面 ============
  let slide = pres.addSlide();
  slide.background = { color: C.darkBg };

  // 装饰形状 - 右上角
  slide.addShape(pres.shapes.OVAL, {
    x: 7.5, y: -1.5, w: 4, h: 4,
    fill: { color: C.teal, transparency: 70 }
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 8.5, y: 3.5, w: 3, h: 3,
    fill: { color: C.accent, transparency: 80 }
  });

  // 图标
  slide.addImage({ data: icons.signal, x: 0.8, y: 0.6, w: 0.7, h: 0.7 });

  // 主标题
  slide.addText("模拟调制与解调", {
    x: 0.8, y: 1.6, w: 8, h: 1.0,
    fontSize: 40, fontFace: FONT_TITLE, color: C.white, bold: true, margin: 0
  });

  // 副标题
  slide.addText("DSB-SC · AM · SSB 原理与MATLAB仿真", {
    x: 0.8, y: 2.6, w: 8, h: 0.6,
    fontSize: 18, fontFace: FONT_BODY, color: C.accent, margin: 0
  });

  // 分隔线
  slide.addShape(pres.shapes.LINE, {
    x: 0.8, y: 3.4, w: 2.5, h: 0,
    line: { color: C.accent, width: 2.5 }
  });

  // 底部信息
  slide.addText([
    { text: "通信系统课程设计 · 实验2", options: { breakLine: true, fontSize: 14, color: C.white, fontFace: FONT_BODY } },
    { text: "yue · 通信工程专业", options: { fontSize: 12, color: C.textMuted, fontFace: FONT_BODY } }
  ], {
    x: 0.8, y: 4.2, w: 6, h: 0.8, margin: 0
  });

  // ============ SLIDE 2: 目录 ============
  slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  // 标题
  slide.addText("目 录", {
    x: 0.8, y: 0.4, w: 4, h: 0.7,
    fontSize: 32, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });
  slide.addShape(pres.shapes.LINE, {
    x: 0.8, y: 1.1, w: 1.2, h: 0,
    line: { color: C.accent, width: 3 }
  });

  const tocItems = [
    { num: "01", title: "调制的基本概念", icon: icons.bookDark },
    { num: "02", title: "DSB-SC 调制与解调", icon: icons.waveDark },
    { num: "03", title: "AM 调制与解调", icon: icons.exchangeDark },
    { num: "04", title: "SSB 调制与解调", icon: icons.cogsDark },
    { num: "05", title: "三种调制方式对比", icon: icons.chartDark },
    { num: "06", title: "MATLAB仿真演示", icon: icons.chipDark },
  ];

  tocItems.forEach((item, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.8 + col * 4.6;
    const y = 1.6 + row * 1.2;

    // 卡片背景
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.2, h: 0.9,
      fill: { color: C.white },
      shadow: cardShadow()
    });

    // 左侧色条
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.06, h: 0.9,
      fill: { color: C.teal }
    });

    // 编号
    slide.addText(item.num, {
      x: x + 0.25, y, w: 0.6, h: 0.9,
      fontSize: 20, fontFace: FONT_TITLE, color: C.teal, bold: true,
      valign: "middle", margin: 0
    });

    // 图标
    slide.addImage({ data: item.icon, x: x + 0.85, y: y + 0.22, w: 0.45, h: 0.45 });

    // 标题
    slide.addText(item.title, {
      x: x + 1.45, y, w: 2.5, h: 0.9,
      fontSize: 15, fontFace: FONT_BODY, color: C.textDark,
      valign: "middle", margin: 0
    });
  });

  // ============ SLIDE 3: 调制的基本概念 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  // 顶部色块
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("调制的基本概念", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 左栏：什么是调制
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 4.2, h: 3.8,
    fill: { color: C.offWhite },
    shadow: cardShadow()
  });

  slide.addImage({ data: icons.signalDark, x: 1.1, y: 1.4, w: 0.4, h: 0.4 });
  slide.addText("什么是调制？", {
    x: 1.6, y: 1.4, w: 3, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.teal, bold: true, valign: "middle", margin: 0
  });

  slide.addText([
    { text: "将基带信号（信息）", options: { breakLine: true } },
    { text: "\"搬运\"到高频载波上", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "为什么要调制？", options: { bold: true, breakLine: true, fontSize: 14, color: C.teal } },
    { text: "", options: { breakLine: true } },
    { text: "• 实现天线有效辐射（天线尺寸 ≈ λ/4）", options: { bullet: true, breakLine: true, fontSize: 13 } },
    { text: "• 频分复用，多路信号互不干扰", options: { bullet: true, breakLine: true, fontSize: 13 } },
    { text: "• 改善传输抗噪声性能", options: { bullet: true, fontSize: 13 } },
  ], {
    x: 1.1, y: 2.0, w: 3.7, h: 2.8,
    fontSize: 13, fontFace: FONT_BODY, color: C.textDark, valign: "top", margin: 0,
    paraSpaceAfter: 4
  });

  // 右栏：调制分类
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.3, y: 1.2, w: 4.2, h: 3.8,
    fill: { color: C.offWhite },
    shadow: cardShadow()
  });

  slide.addImage({ data: icons.cogsDark, x: 5.6, y: 1.4, w: 0.4, h: 0.4 });
  slide.addText("模拟调制的分类", {
    x: 6.1, y: 1.4, w: 3, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.teal, bold: true, valign: "middle", margin: 0
  });

  // 分类图 - 用形状模拟
  const catY = 2.1;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.8, y: catY, w: 3.2, h: 0.5,
    fill: { color: C.darkBg }
  });
  slide.addText("模拟调制", {
    x: 5.8, y: catY, w: 3.2, h: 0.5,
    fontSize: 14, fontFace: FONT_BODY, color: C.white, bold: true, align: "center", valign: "middle", margin: 0
  });

  const subY = catY + 0.7;
  const subs = [
    { label: "幅度调制", x: 5.8, color: C.teal },
    { label: "角度调制", x: 7.5, color: C.midnight },
  ];
  subs.forEach((s, i) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: s.x, y: subY, w: 1.5, h: 0.45,
      fill: { color: s.color }
    });
    slide.addText(s.label, {
      x: s.x, y: subY, w: 1.5, h: 0.45,
      fontSize: 12, fontFace: FONT_BODY, color: C.white, align: "center", valign: "middle", margin: 0
    });
  });

  // 幅度调制子项
  const amSubs = [
    { label: "DSB-SC", x: 5.8 },
    { label: "AM", x: 6.5 },
    { label: "SSB", x: 7.2 },
  ];
  amSubs.forEach((s, i) => {
    const yy = subY + 0.65;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: s.x, y: yy, w: 0.65, h: 0.4,
      fill: { color: C.light }
    });
    slide.addText(s.label, {
      x: s.x, y: yy, w: 0.65, h: 0.4,
      fontSize: 10, fontFace: FONT_BODY, color: C.textDark, align: "center", valign: "middle", margin: 0
    });
  });

  // 底部提示
  slide.addText("💡 本讲聚焦幅度调制（线性调制）的三种方式", {
    x: 0.8, y: 5.1, w: 8, h: 0.4,
    fontSize: 12, fontFace: FONT_BODY, color: C.textMuted, italic: true, margin: 0
  });

  // ============ SLIDE 4: DSB-SC 调制 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("DSB-SC 调制与解调", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 左侧：原理
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 5.5, h: 4.0,
    fill: { color: C.offWhite },
    shadow: cardShadow()
  });

  slide.addText("原理", {
    x: 1.1, y: 1.35, w: 2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.teal, bold: true, margin: 0
  });

  slide.addText([
    { text: "时域表达式：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "s(t) = m(t) · cos(2πfct)", options: { breakLine: true, fontSize: 14, fontFace: "Consolas", color: C.teal } },
    { text: "", options: { breakLine: true } },
    { text: "频域：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "基带频谱搬移到 ±fc 处", options: { breakLine: true, fontSize: 13 } },
    { text: "无载波分量 → 功率效率高", options: { breakLine: true, fontSize: 13 } },
    { text: "", options: { breakLine: true } },
    { text: "解调方式：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "必须使用 相干解调（同步解调）", options: { fontSize: 13, color: C.midnight } },
  ], {
    x: 1.1, y: 1.85, w: 5.0, h: 3.0,
    fontSize: 13, fontFace: FONT_BODY, color: C.textDark, valign: "top", margin: 0,
    paraSpaceAfter: 3
  });

  // 右侧：关键特点
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.6, y: 1.2, w: 2.8, h: 4.0,
    fill: { color: C.darkBg }
  });

  slide.addText("关键特点", {
    x: 6.9, y: 1.4, w: 2.2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.accent, bold: true, margin: 0
  });

  slide.addText([
    { text: "✅ 无载波功率浪费", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "✅ 带宽 = 2B", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "  （B为基带带宽）", options: { breakLine: true, fontSize: 11, color: C.textMuted } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 需要本地载波同步", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 接收端复杂度高", options: { fontSize: 13, color: C.white } },
  ], {
    x: 6.9, y: 2.0, w: 2.3, h: 2.8,
    fontSize: 13, fontFace: FONT_BODY, valign: "top", margin: 0,
    paraSpaceAfter: 2
  });

  // ============ SLIDE 5: AM 调制 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("AM 调制与解调", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 左栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 5.5, h: 4.0,
    fill: { color: C.offWhite },
    shadow: cardShadow()
  });

  slide.addText("原理", {
    x: 1.1, y: 1.35, w: 2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.teal, bold: true, margin: 0
  });

  slide.addText([
    { text: "时域表达式：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "s(t) = [A₀ + m(t)] · cos(2πfct)", options: { breakLine: true, fontSize: 14, fontFace: "Consolas", color: C.teal } },
    { text: "", options: { breakLine: true } },
    { text: "其中 A₀ 为直流偏置", options: { breakLine: true, fontSize: 13 } },
    { text: "需满足 A₀ ≥ |m(t)|max 避免过调制", options: { breakLine: true, fontSize: 13 } },
    { text: "", options: { breakLine: true } },
    { text: "解调方式：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "包络检波（非相干解调）", options: { fontSize: 13, color: C.midnight } },
  ], {
    x: 1.1, y: 1.85, w: 5.0, h: 3.0,
    fontSize: 13, fontFace: FONT_BODY, color: C.textDark, valign: "top", margin: 0,
    paraSpaceAfter: 3
  });

  // 右栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.6, y: 1.2, w: 2.8, h: 4.0,
    fill: { color: C.darkBg }
  });

  slide.addText("关键特点", {
    x: 6.9, y: 1.4, w: 2.2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.accent, bold: true, margin: 0
  });

  slide.addText([
    { text: "✅ 解调简单（包络检波）", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "✅ 接收端成本低", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 载波功率浪费", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "  （功率效率 ≤ 50%）", options: { breakLine: true, fontSize: 11, color: C.textMuted } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 带宽 = 2B", options: { fontSize: 13, color: C.white } },
  ], {
    x: 6.9, y: 2.0, w: 2.3, h: 2.8,
    fontSize: 13, fontFace: FONT_BODY, valign: "top", margin: 0,
    paraSpaceAfter: 2
  });

  // ============ SLIDE 6: SSB 调制 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("SSB 调制与解调", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 左栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 5.5, h: 4.0,
    fill: { color: C.offWhite },
    shadow: cardShadow()
  });

  slide.addText("原理", {
    x: 1.1, y: 1.35, w: 2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.teal, bold: true, margin: 0
  });

  slide.addText([
    { text: "SSB = DSB-SC 的一个边带", options: { breakLine: true, fontSize: 14, bold: true } },
    { text: "", options: { breakLine: true } },
    { text: "生成方法：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "① 滤波法：DSB-SC → 边带滤波器", options: { breakLine: true, fontSize: 13 } },
    { text: "② 相移法：希尔伯特变换", options: { breakLine: true, fontSize: 13 } },
    { text: "", options: { breakLine: true } },
    { text: "解调方式：", options: { bold: true, breakLine: true, fontSize: 14 } },
    { text: "必须使用 相干解调", options: { breakLine: true, fontSize: 13, color: C.midnight } },
    { text: "", options: { breakLine: true } },
    { text: "时域表达式（上边带）：", options: { bold: true, breakLine: true, fontSize: 13 } },
    { text: "s(t) = m(t)cos(ωct) − m̂(t)sin(ωct)", options: { fontSize: 13, fontFace: "Consolas", color: C.teal } },
  ], {
    x: 1.1, y: 1.85, w: 5.0, h: 3.0,
    fontSize: 13, fontFace: FONT_BODY, color: C.textDark, valign: "top", margin: 0,
    paraSpaceAfter: 2
  });

  // 右栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.6, y: 1.2, w: 2.8, h: 4.0,
    fill: { color: C.darkBg }
  });

  slide.addText("关键特点", {
    x: 6.9, y: 1.4, w: 2.2, h: 0.4,
    fontSize: 16, fontFace: FONT_BODY, color: C.accent, bold: true, margin: 0
  });

  slide.addText([
    { text: "✅ 带宽 = B（最省带宽）", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "✅ 无载波功率浪费", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 生成电路复杂", options: { breakLine: true, fontSize: 13, color: C.white } },
    { text: "  （滤波器要求高）", options: { breakLine: true, fontSize: 11, color: C.textMuted } },
    { text: "", options: { breakLine: true } },
    { text: "⚠️ 需要相干解调", options: { fontSize: 13, color: C.white } },
  ], {
    x: 6.9, y: 2.0, w: 2.3, h: 2.8,
    fontSize: 13, fontFace: FONT_BODY, valign: "top", margin: 0,
    paraSpaceAfter: 2
  });

  // ============ SLIDE 7: 三种调制方式对比 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("三种调制方式对比", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 对比表格
  const tableHeader = [
    { text: "对比项", options: { fill: { color: C.darkBg }, color: C.white, bold: true, fontSize: 13, fontFace: FONT_BODY, align: "center", valign: "middle" } },
    { text: "DSB-SC", options: { fill: { color: C.darkBg }, color: C.white, bold: true, fontSize: 13, fontFace: FONT_BODY, align: "center", valign: "middle" } },
    { text: "AM", options: { fill: { color: C.darkBg }, color: C.white, bold: true, fontSize: 13, fontFace: FONT_BODY, align: "center", valign: "middle" } },
    { text: "SSB", options: { fill: { color: C.darkBg }, color: C.white, bold: true, fontSize: 13, fontFace: FONT_BODY, align: "center", valign: "middle" } },
  ];

  const rowStyle = (i) => ({
    fill: { color: i % 2 === 0 ? C.offWhite : C.white },
    fontSize: 12, fontFace: FONT_BODY, color: C.textDark, valign: "middle"
  });

  const tableData = [
    tableHeader,
    [
      { text: "时域表达式", options: { ...rowStyle(0), bold: true } },
      { text: "m(t)·cos(ωct)", options: rowStyle(0) },
      { text: "[A₀+m(t)]·cos(ωct)", options: rowStyle(0) },
      { text: "m(t)cos(ωct)∓m̂(t)sin(ωct)", options: rowStyle(0) },
    ],
    [
      { text: "带宽", options: { ...rowStyle(1), bold: true } },
      { text: "2B", options: rowStyle(1) },
      { text: "2B", options: rowStyle(1) },
      { text: "B", options: { ...rowStyle(1), color: C.accent, bold: true } },
    ],
    [
      { text: "载波分量", options: { ...rowStyle(0), bold: true } },
      { text: "无 ✓", options: rowStyle(0) },
      { text: "有 ✗", options: rowStyle(0) },
      { text: "无 ✓", options: rowStyle(0) },
    ],
    [
      { text: "解调方式", options: { ...rowStyle(1), bold: true } },
      { text: "相干解调", options: rowStyle(1) },
      { text: "包络检波", options: { ...rowStyle(1), color: C.accent, bold: true } },
      { text: "相干解调", options: rowStyle(1) },
    ],
    [
      { text: "功率效率", options: { ...rowStyle(0), bold: true } },
      { text: "高", options: { ...rowStyle(0), color: C.accent, bold: true } },
      { text: "低 (≤50%)", options: rowStyle(0) },
      { text: "高", options: { ...rowStyle(0), color: C.accent, bold: true } },
    ],
    [
      { text: "接收端复杂度", options: { ...rowStyle(1), bold: true } },
      { text: "高", options: rowStyle(1) },
      { text: "低", options: { ...rowStyle(1), color: C.accent, bold: true } },
      { text: "高", options: rowStyle(1) },
    ],
  ];

  slide.addTable(tableData, {
    x: 0.8, y: 1.2, w: 8.4,
    colW: [1.8, 2.2, 2.2, 2.2],
    border: { pt: 0.5, color: "D0D8E0" },
    rowH: [0.5, 0.55, 0.5, 0.5, 0.5, 0.5, 0.5],
  });

  // 底部总结
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 4.6, w: 8.4, h: 0.7,
    fill: { color: C.light }
  });
  slide.addText("核心权衡：节省功率 / 带宽 → 接收端复杂度增加", {
    x: 0.8, y: 4.6, w: 8.4, h: 0.7,
    fontSize: 14, fontFace: FONT_BODY, color: C.textDark, bold: true,
    align: "center", valign: "middle", margin: 0
  });

  // ============ SLIDE 8: MATLAB仿真 ============
  slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: C.teal }
  });

  slide.addText("MATLAB 仿真演示", {
    x: 0.8, y: 0.3, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.textDark, bold: true, margin: 0
  });

  // 三个仿真卡片
  const sims = [
    {
      title: "DSB-SC 仿真",
      items: [
        "生成基带信号 m(t)",
        "与载波相乘得 s(t)",
        "FFT 观察频谱搬移",
        "相干解调恢复 m(t)"
      ],
      x: 0.8, color: C.teal
    },
    {
      title: "AM 仿真",
      items: [
        "添加直流偏置 A₀",
        "调制 → 观察过调制",
        "包络检波解调",
        "对比不同调幅指数"
      ],
      x: 3.6, color: C.midnight
    },
    {
      title: "SSB 仿真",
      items: [
        "DSB-SC 信号生成",
        "理想带通滤波器",
        "保留上/下边带",
        "相干解调验证"
      ],
      x: 6.4, color: C.darkBg
    },
  ];

  sims.forEach((sim) => {
    // 卡片背景
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sim.x, y: 1.2, w: 2.6, h: 3.2,
      fill: { color: C.offWhite },
      shadow: cardShadow()
    });

    // 顶部色条
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sim.x, y: 1.2, w: 2.6, h: 0.06,
      fill: { color: sim.color }
    });

    // 标题
    slide.addText(sim.title, {
      x: sim.x + 0.15, y: 1.4, w: 2.3, h: 0.4,
      fontSize: 14, fontFace: FONT_BODY, color: sim.color, bold: true, margin: 0
    });

    // 步骤列表
    const stepTexts = sim.items.map((item, idx) => ({
      text: `${idx + 1}. ${item}`,
      options: { breakLine: idx < sim.items.length - 1, fontSize: 12, color: C.textDark }
    }));

    slide.addText(stepTexts, {
      x: sim.x + 0.15, y: 1.9, w: 2.3, h: 2.2,
      fontSize: 12, fontFace: FONT_BODY, valign: "top", margin: 0,
      paraSpaceAfter: 6
    });
  });

  // 底部提示
  slide.addText("💡 仿真中注意：采样频率需设为载波频率的 8~10 倍以上，避免频谱混叠", {
    x: 0.8, y: 4.6, w: 8.4, h: 0.4,
    fontSize: 12, fontFace: FONT_BODY, color: C.textMuted, italic: true, margin: 0
  });

  // ============ SLIDE 9: 关键知识点总结 ============
  slide = pres.addSlide();
  slide.background = { color: C.darkBg };

  // 装饰
  slide.addShape(pres.shapes.OVAL, {
    x: -1, y: -1, w: 3.5, h: 3.5,
    fill: { color: C.teal, transparency: 75 }
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 8, y: 3.5, w: 3, h: 3,
    fill: { color: C.accent, transparency: 80 }
  });

  slide.addText("关键知识点总结", {
    x: 0.8, y: 0.4, w: 8, h: 0.7,
    fontSize: 28, fontFace: FONT_TITLE, color: C.white, bold: true, margin: 0
  });

  slide.addShape(pres.shapes.LINE, {
    x: 0.8, y: 1.1, w: 1.5, h: 0,
    line: { color: C.accent, width: 3 }
  });

  const points = [
    { icon: icons.waveDark, text: "DSB-SC：无载波、带宽 2B、需相干解调" },
    { icon: icons.exchangeDark, text: "AM：有载波、带宽 2B、可用包络检波（最简单）" },
    { icon: icons.cogsDark, text: "SSB：无载波、带宽 B（最省）、需相干解调" },
    { icon: icons.chartDark, text: "核心权衡：节省功率/带宽 → 接收端复杂度增加" },
    { icon: icons.chipDark, text: "仿真注意：采样频率 ≥ 8~10 倍载波频率" },
  ];

  points.forEach((p, i) => {
    const y = 1.5 + i * 0.75;

    // 图标圆
    slide.addShape(pres.shapes.OVAL, {
      x: 0.8, y: y + 0.05, w: 0.45, h: 0.45,
      fill: { color: C.teal, transparency: 50 }
    });
    slide.addImage({ data: p.icon, x: 0.88, y: y + 0.13, w: 0.3, h: 0.3 });

    slide.addText(p.text, {
      x: 1.5, y, w: 7.5, h: 0.55,
      fontSize: 15, fontFace: FONT_BODY, color: C.white,
      valign: "middle", margin: 0
    });
  });

  // ============ SLIDE 10: 结束页 ============
  slide = pres.addSlide();
  slide.background = { color: C.midnight };

  // 装饰
  slide.addShape(pres.shapes.OVAL, {
    x: 7, y: -1, w: 4.5, h: 4.5,
    fill: { color: C.teal, transparency: 75 }
  });
  slide.addShape(pres.shapes.OVAL, {
    x: -1.5, y: 3, w: 4, h: 4,
    fill: { color: C.accent, transparency: 80 }
  });

  slide.addImage({ data: icons.rocket, x: 4.5, y: 1.0, w: 0.8, h: 0.8 });

  slide.addText("谢谢！", {
    x: 1, y: 2.0, w: 8, h: 1.0,
    fontSize: 44, fontFace: FONT_TITLE, color: C.white, bold: true,
    align: "center", valign: "middle", margin: 0
  });

  slide.addText("Questions & Discussion", {
    x: 1, y: 3.0, w: 8, h: 0.5,
    fontSize: 18, fontFace: FONT_BODY, color: C.accent,
    align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.LINE, {
    x: 4.2, y: 3.7, w: 1.6, h: 0,
    line: { color: C.accent, width: 2 }
  });

  slide.addText("yue · 通信工程", {
    x: 1, y: 4.0, w: 8, h: 0.4,
    fontSize: 13, fontFace: FONT_BODY, color: C.textMuted,
    align: "center", valign: "middle", margin: 0
  });

  // ============ 保存 ============
  const outputPath = "./模拟调制与解调.pptx";
  await pres.writeFile({ fileName: outputPath });
  console.log("PPT generated: " + outputPath);
  return outputPath;
}

createPresentation().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});