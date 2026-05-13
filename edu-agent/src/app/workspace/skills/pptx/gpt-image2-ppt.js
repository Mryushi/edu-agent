const pptxgen = require("C:/Users/asus/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// Icon imports
const { FaRocket, FaMagic, FaImage, FaBrain, FaStar, FaChartBar, FaLightbulb, FaCog, FaCheckCircle, FaArrowRight } = require("react-icons/fa");

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

// Color palette - Deep Tech / AI theme
const C = {
  darkBg: "0F172A",       // 深空蓝黑
  darkBg2: "1E293B",      // 稍浅深色
  accent: "06B6D4",       // 霓虹青
  accent2: "22D3EE",      // 亮青
  purple: "8B5CF6",       // 紫色
  white: "FFFFFF",
  lightGray: "CBD5E1",
  midGray: "64748B",
  cardBg: "1E293B",
  cardBorder: "334155",
  orange: "F97316",
  pink: "EC4899",
};

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "AI 分享";
  pres.title = "GPT Images 2.0 - AI 文生图的新纪元";

  // Pre-render icons
  const iconRocket = await iconToBase64Png(FaRocket, "#" + C.accent, 256);
  const iconMagic = await iconToBase64Png(FaMagic, "#" + C.accent, 256);
  const iconImage = await iconToBase64Png(FaImage, "#" + C.accent, 256);
  const iconBrain = await iconToBase64Png(FaBrain, "#" + C.purple, 256);
  const iconStar = await iconToBase64Png(FaStar, "#" + C.orange, 256);
  const iconChart = await iconToBase64Png(FaChartBar, "#" + C.accent, 256);
  const iconBulb = await iconToBase64Png(FaLightbulb, "#" + C.orange, 256);
  const iconCog = await iconToBase64Png(FaCog, "#" + C.midGray, 256);
  const iconCheck = await iconToBase64Png(FaCheckCircle, "#" + C.accent, 256);
  const iconArrow = await iconToBase64Png(FaArrowRight, "#" + C.accent, 256);
  const iconCheckWhite = await iconToBase64Png(FaCheckCircle, "#" + C.white, 256);
  const iconStarWhite = await iconToBase64Png(FaStar, "#" + C.white, 256);
  const iconRocketWhite = await iconToBase64Png(FaRocket, "#" + C.white, 256);

  // ==========================================
  // SLIDE 1: 封面
  // ==========================================
  let s1 = pres.addSlide();
  s1.background = { color: C.darkBg };

  // 装饰性顶部渐变条
  s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  // 主标题
  s1.addText("GPT Images 2.0", {
    x: 0.8, y: 1.2, w: 8.4, h: 1.2,
    fontSize: 48, fontFace: "Arial Black", color: C.white, bold: true, align: "center", margin: 0,
  });

  // 副标题
  s1.addText("AI 文生图的新纪元", {
    x: 0.8, y: 2.3, w: 8.4, h: 0.7,
    fontSize: 24, fontFace: "Calibri", color: C.accent, align: "center", margin: 0,
  });

  // 装饰线
  s1.addShape(pres.shapes.LINE, {
    x: 3.5, y: 3.2, w: 3, h: 0,
    line: { color: C.accent, width: 2 },
  });

  // 图标行
  s1.addImage({ data: iconRocket, x: 3.8, y: 3.5, w: 0.5, h: 0.5 });
  s1.addImage({ data: iconMagic, x: 4.5, y: 3.5, w: 0.5, h: 0.5 });
  s1.addImage({ data: iconImage, x: 5.2, y: 3.5, w: 0.5, h: 0.5 });

  // 底部信息
  s1.addText("兴趣小组分享  ·  2026", {
    x: 0.8, y: 4.6, w: 8.4, h: 0.4,
    fontSize: 14, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
  });

  // ==========================================
  // SLIDE 2: 目录
  // ==========================================
  let s2 = pres.addSlide();
  s2.background = { color: C.darkBg };

  s2.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s2.addText("目  录", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.8,
    fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  const tocItems = [
    { num: "01", title: "GPT Images 2.0 是什么", icon: iconMagic },
    { num: "02", title: "核心能力突破", icon: iconBrain },
    { num: "03", title: "横向对比：强在哪？", icon: iconChart },
    { num: "04", title: "应用场景", icon: iconBulb },
    { num: "05", title: "上手体验 & 提示词技巧", icon: iconCog },
    { num: "06", title: "总结 & 展望", icon: iconStar },
  ];

  tocItems.forEach((item, i) => {
    const yPos = 1.5 + i * 0.65;
    // 编号
    s2.addText(item.num, {
      x: 0.8, y: yPos, w: 0.6, h: 0.5,
      fontSize: 20, fontFace: "Arial Black", color: C.accent, bold: true, align: "center", valign: "middle", margin: 0,
    });
    // 分隔竖线
    s2.addShape(pres.shapes.LINE, {
      x: 1.5, y: yPos + 0.05, w: 0, h: 0.4,
      line: { color: C.cardBorder, width: 1 },
    });
    // 图标
    s2.addImage({ data: item.icon, x: 1.7, y: yPos + 0.08, w: 0.35, h: 0.35 });
    // 标题
    s2.addText(item.title, {
      x: 2.2, y: yPos, w: 6, h: 0.5,
      fontSize: 18, fontFace: "Calibri", color: C.lightGray, valign: "middle", margin: 0,
    });
  });

  // ==========================================
  // SLIDE 3: GPT Images 2.0 是什么
  // ==========================================
  let s3 = pres.addSlide();
  s3.background = { color: C.darkBg };
  s3.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s3.addText("GPT Images 2.0 是什么", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  // 左侧卡片 - 发布时间
  const makeCard = (x, y, w, h, icon, title, desc) => {
    s3.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.3 },
    });
    s3.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.06, h,
      fill: { color: C.accent },
    });
    s3.addImage({ data: icon, x: x + 0.3, y: y + 0.2, w: 0.4, h: 0.4 });
    s3.addText(title, {
      x: x + 0.85, y: y + 0.15, w: w - 1.1, h: 0.4,
      fontSize: 16, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
    });
    s3.addText(desc, {
      x: x + 0.3, y: y + 0.6, w: w - 0.6, h: h - 0.8,
      fontSize: 13, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  };

  makeCard(0.8, 1.3, 4.1, 1.6, iconMagic,
    "2026年4月22日发布",
    "OpenAI 最新图像生成模型\n在 Image Arena 所有榜单登顶\n文生图榜单以 242 分优势断层第一"
  );

  makeCard(5.1, 1.3, 4.1, 1.6, iconRocket,
    "全面超越前代",
    "文本渲染、写实人像、语义理解\n三大核心能力全面突破\n总分 1512 分，拉开代际差距"
  );

  // 底部大卡片 - 一句话总结
  s3.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.3, w: 8.4, h: 1.6,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.3 },
  });
  s3.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.3, w: 8.4, h: 0.06,
    fill: { color: C.purple },
  });

  s3.addText("一句话总结", {
    x: 1.2, y: 3.5, w: 7.6, h: 0.4,
    fontSize: 14, fontFace: "Calibri", color: C.purple, bold: true, margin: 0,
  });
  s3.addText("GPT Images 2.0 是目前综合能力最强的 AI 文生图模型，在文本渲染、语义理解、写实质感上实现了质的飞跃。", {
    x: 1.2, y: 3.9, w: 7.6, h: 0.8,
    fontSize: 16, fontFace: "Calibri", color: C.lightGray, margin: 0,
  });

  // ==========================================
  // SLIDE 4: 核心能力突破
  // ==========================================
  let s4 = pres.addSlide();
  s4.background = { color: C.darkBg };
  s4.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s4.addText("核心能力突破", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  const abilities = [
    { icon: iconCheck, title: "文本渲染", desc: "中英文文字清晰准确\n告别\"乱码文字\"时代", color: C.accent },
    { icon: iconCheck, title: "语义理解", desc: "复杂提示词精准遵循\n抽象概念也能完美呈现", color: C.purple },
    { icon: iconCheck, title: "写实质感", desc: "人像细节大幅提升\n\"AI 味\"显著减少", color: C.orange },
    { icon: iconCheck, title: "逻辑一致性", desc: "多物体场景布局合理\n光影关系更自然", color: C.pink },
  ];

  abilities.forEach((item, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.8 + col * 4.6;
    const y = 1.3 + row * 1.9;

    s4.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.2, h: 1.6,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
    });
    s4.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.2, h: 0.04,
      fill: { color: item.color },
    });
    s4.addImage({ data: item.icon, x: x + 0.3, y: y + 0.3, w: 0.35, h: 0.35 });
    s4.addText(item.title, {
      x: x + 0.8, y: y + 0.25, w: 3, h: 0.4,
      fontSize: 18, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
    });
    s4.addText(item.desc, {
      x: x + 0.3, y: y + 0.7, w: 3.6, h: 0.8,
      fontSize: 13, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  });

  // ==========================================
  // SLIDE 5: 榜单数据
  // ==========================================
  let s5 = pres.addSlide();
  s5.background = { color: C.darkBg };
  s5.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s5.addText("榜单表现：断层领先", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  // 大数字展示
  const stats = [
    { num: "1512", label: "总分", sub: "Image Arena 榜首" },
    { num: "242", label: "领先分差", sub: "文生图榜单最大分差纪录" },
    { num: "6", label: "细分第一", sub: "文本/肖像/动漫等均第一" },
  ];

  stats.forEach((item, i) => {
    const x = 0.8 + i * 3.1;
    s5.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.3, w: 2.7, h: 1.8,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
    });
    s5.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.3, w: 2.7, h: 0.04,
      fill: { color: i === 1 ? C.orange : C.accent },
    });
    s5.addText(item.num, {
      x, y: 1.5, w: 2.7, h: 0.7,
      fontSize: 40, fontFace: "Arial Black", color: i === 1 ? C.orange : C.accent, bold: true, align: "center", margin: 0,
    });
    s5.addText(item.label, {
      x, y: 2.15, w: 2.7, h: 0.35,
      fontSize: 14, fontFace: "Calibri", color: C.white, bold: true, align: "center", margin: 0,
    });
    s5.addText(item.sub, {
      x, y: 2.45, w: 2.7, h: 0.35,
      fontSize: 11, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
    });
  });

  // 底部说明
  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.5, w: 8.4, h: 1.4,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
  });
  s5.addText([
    { text: "Image Arena 排行榜", options: { bold: true, color: "#" + C.white, fontSize: 16, breakLine: true } },
    { text: "GPT Images 2.0 在发布后迅速登顶所有榜单，在文生图、文本渲染、肖像、卡通动漫等细分领域均位列第一，创下该平台最大分差纪录。", options: { color: "#" + C.lightGray, fontSize: 13 } },
  ], {
    x: 1.2, y: 3.65, w: 7.6, h: 1.1, fontFace: "Calibri", margin: 0,
  });

  // ==========================================
  // SLIDE 6: 横向对比
  // ==========================================
  let s6 = pres.addSlide();
  s6.background = { color: C.darkBg };
  s6.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s6.addText("横向对比：强在哪？", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  // 表格
  const tableHeader = [
    { text: "对比维度", options: { fill: { color: C.accent }, color: "FFFFFF", bold: true, fontSize: 13, fontFace: "Calibri", align: "center", valign: "middle" } },
    { text: "GPT Images 2.0", options: { fill: { color: C.accent }, color: "FFFFFF", bold: true, fontSize: 13, fontFace: "Calibri", align: "center", valign: "middle" } },
    { text: "Midjourney V6", options: { fill: { color: C.accent }, color: "FFFFFF", bold: true, fontSize: 13, fontFace: "Calibri", align: "center", valign: "middle" } },
    { text: "DALL·E 3", options: { fill: { color: C.accent }, color: "FFFFFF", bold: true, fontSize: 13, fontFace: "Calibri", align: "center", valign: "middle" } },
  ];

  const rowStyle = (isAlt) => ({
    fill: { color: isAlt ? C.cardBg : C.darkBg2 },
    color: C.lightGray, fontSize: 12, fontFace: "Calibri", align: "center", valign: "middle",
  });

  const tableRows = [
    tableHeader,
    [
      { text: "文本渲染", options: { ...rowStyle(false), bold: true, color: "#" + C.white } },
      { text: "⭐⭐⭐⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐⭐", options: rowStyle(false) },
    ],
    [
      { text: "语义理解", options: { ...rowStyle(true), bold: true, color: "#" + C.white } },
      { text: "⭐⭐⭐⭐⭐", options: rowStyle(true) },
      { text: "⭐⭐⭐⭐", options: rowStyle(true) },
      { text: "⭐⭐⭐⭐", options: rowStyle(true) },
    ],
    [
      { text: "写实质感", options: { ...rowStyle(false), bold: true, color: "#" + C.white } },
      { text: "⭐⭐⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐⭐⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐⭐", options: rowStyle(false) },
    ],
    [
      { text: "易用性", options: { ...rowStyle(true), bold: true, color: "#" + C.white } },
      { text: "⭐⭐⭐⭐⭐", options: rowStyle(true) },
      { text: "⭐⭐⭐", options: rowStyle(true) },
      { text: "⭐⭐⭐⭐", options: rowStyle(true) },
    ],
    [
      { text: "价格门槛", options: { ...rowStyle(false), bold: true, color: "#" + C.white } },
      { text: "⭐⭐⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐⭐", options: rowStyle(false) },
      { text: "⭐⭐⭐⭐⭐", options: rowStyle(false) },
    ],
  ];

  s6.addTable(tableRows, {
    x: 0.8, y: 1.2, w: 8.4,
    colW: [1.8, 2.2, 2.2, 2.2],
    rowH: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    border: { pt: 0.5, color: C.cardBorder },
  });

  // 底部结论
  s6.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 4.4, w: 8.4, h: 0.8,
    fill: { color: C.cardBg },
  });
  s6.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 4.4, w: 0.06, h: 0.8,
    fill: { color: C.orange },
  });
  s6.addText("结论：GPT Images 2.0 综合实力最强，尤其在文本渲染和易用性上遥遥领先", {
    x: 1.1, y: 4.5, w: 7.8, h: 0.6,
    fontSize: 14, fontFace: "Calibri", color: C.lightGray, valign: "middle", margin: 0,
  });

  // ==========================================
  // SLIDE 7: 应用场景
  // ==========================================
  let s7 = pres.addSlide();
  s7.background = { color: C.darkBg };
  s7.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s7.addText("应用场景", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  const scenes = [
    { icon: iconBulb, title: "创意设计", desc: "海报、封面、插画\n快速生成设计素材" },
    { icon: iconImage, title: "内容创作", desc: "文章配图、社交媒体\n视频封面、缩略图" },
    { icon: iconStar, title: "电商营销", desc: "产品展示图、广告banner\n排版文字一键生成" },
    { icon: iconCog, title: "游戏/动漫", desc: "角色概念设计\n场景原画、卡通形象" },
  ];

  scenes.forEach((item, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.8 + col * 4.6;
    const y = 1.3 + row * 1.9;

    s7.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.2, h: 1.6,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
    });
    s7.addImage({ data: item.icon, x: x + 0.3, y: y + 0.25, w: 0.4, h: 0.4 });
    s7.addText(item.title, {
      x: x + 0.85, y: y + 0.2, w: 3, h: 0.4,
      fontSize: 18, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
    });
    s7.addText(item.desc, {
      x: x + 0.3, y: y + 0.7, w: 3.6, h: 0.8,
      fontSize: 13, fontFace: "Calibri", color: C.lightGray, margin: 0,
    });
  });

  // ==========================================
  // SLIDE 8: 上手体验 & 提示词技巧
  // ==========================================
  let s8 = pres.addSlide();
  s8.background = { color: C.darkBg };
  s8.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s8.addText("上手体验 & 提示词技巧", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  // 左侧：怎么用
  s8.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 4.1, h: 3.8,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
  });
  s8.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 4.1, h: 0.04,
    fill: { color: C.accent },
  });
  s8.addText("如何使用", {
    x: 1.1, y: 1.4, w: 3.5, h: 0.4,
    fontSize: 18, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
  });
  s8.addText([
    { text: "1. 打开 ChatGPT（需 Plus/Pro 订阅）", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "2. 选择 GPT-4o 或 GPT Image 2 模型", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "3. 用自然语言描述你想要的图片", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "4. 可迭代修改：\"把背景换成红色\"", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "5. 支持 API 调用，开发者友好", options: { fontSize: 13, color: "#" + C.lightGray } },
  ], {
    x: 1.1, y: 2.0, w: 3.5, h: 2.8, fontFace: "Calibri", margin: 0, paraSpaceAfter: 6,
  });

  // 右侧：提示词技巧
  s8.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.2, w: 4.1, h: 3.8,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
  });
  s8.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.2, w: 4.1, h: 0.04,
    fill: { color: C.orange },
  });
  s8.addText("提示词技巧", {
    x: 5.4, y: 1.4, w: 3.5, h: 0.4,
    fontSize: 18, fontFace: "Calibri", color: C.white, bold: true, margin: 0,
  });
  s8.addText([
    { text: "🎯 具体描述风格", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "    \"赛博朋克风，霓虹灯光\"", options: { breakLine: true, fontSize: 12, color: "#" + C.midGray } },
    { text: "🎯 指定构图方式", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "    \"特写镜头，浅景深效果\"", options: { breakLine: true, fontSize: 12, color: "#" + C.midGray } },
    { text: "🎯 包含文字时明确说明", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "    \"海报上写「AI 未来」\"", options: { breakLine: true, fontSize: 12, color: "#" + C.midGray } },
    { text: "🎯 迭代修改更高效", options: { breakLine: true, fontSize: 13, color: "#" + C.lightGray } },
    { text: "    \"把色调调暗，增加颗粒感\"", options: { fontSize: 12, color: "#" + C.midGray } },
  ], {
    x: 5.4, y: 2.0, w: 3.5, h: 2.8, fontFace: "Calibri", margin: 0, paraSpaceAfter: 4,
  });

  // ==========================================
  // SLIDE 9: 现场演示 - 图片占位
  // ==========================================
  let s9 = pres.addSlide();
  s9.background = { color: C.darkBg };
  s9.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s9.addText("现场演示", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0,
  });

  // 图片占位区域
  s9.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 4.1, h: 3.2,
    fill: { color: C.cardBg },
    line: { color: C.cardBorder, width: 1, dashType: "dash" },
  });
  s9.addText("📷 示例图 1", {
    x: 0.8, y: 2.5, w: 4.1, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.midGray, align: "center", valign: "middle", margin: 0,
  });
  s9.addText("提示词：赛博朋克城市夜景，霓虹灯牌上写「GPT」", {
    x: 0.8, y: 3.8, w: 4.1, h: 0.4,
    fontSize: 10, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
  });

  s9.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.2, w: 4.1, h: 3.2,
    fill: { color: C.cardBg },
    line: { color: C.cardBorder, width: 1, dashType: "dash" },
  });
  s9.addText("📷 示例图 2", {
    x: 5.1, y: 2.5, w: 4.1, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.midGray, align: "center", valign: "middle", margin: 0,
  });
  s9.addText("提示词：写实人像，自然光，电影质感", {
    x: 5.1, y: 3.8, w: 4.1, h: 0.4,
    fontSize: 10, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
  });

  // ==========================================
  // SLIDE 10: 总结 & 展望
  // ==========================================
  let s10 = pres.addSlide();
  s10.background = { color: C.darkBg };
  s10.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  s10.addText("总结 & 展望", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.8,
    fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, align: "center", margin: 0,
  });

  // 总结卡片
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.5, w: 8.4, h: 2.2,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.3 },
  });
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.5, w: 0.06, h: 2.2,
    fill: { color: C.accent },
  });

  s10.addText([
    { text: "✅ 文本渲染能力质的飞跃", options: { breakLine: true, fontSize: 15, color: "#" + C.lightGray } },
    { text: "✅ 语义理解精准，易用性极强", options: { breakLine: true, fontSize: 15, color: "#" + C.lightGray } },
    { text: "✅ 写实质感大幅提升，综合实力断层领先", options: { breakLine: true, fontSize: 15, color: "#" + C.lightGray } },
    { text: "✅ 与 ChatGPT 深度集成，迭代修改极其方便", options: { fontSize: 15, color: "#" + C.lightGray } },
  ], {
    x: 1.2, y: 1.7, w: 7.6, h: 1.8, fontFace: "Calibri", margin: 0, paraSpaceAfter: 8,
  });

  // 展望
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 4.0, w: 8.4, h: 1.0,
    fill: { color: C.cardBg },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.3 },
  });
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 4.0, w: 0.06, h: 1.0,
    fill: { color: C.orange },
  });
  s10.addText("🔮 展望：AI 生图正在从\"能看\"走向\"能用\"，未来将深度融入设计、营销、内容创作全流程", {
    x: 1.2, y: 4.1, w: 7.6, h: 0.8,
    fontSize: 14, fontFace: "Calibri", color: C.lightGray, valign: "middle", margin: 0,
  });

  // ==========================================
  // SLIDE 11: 谢谢
  // ==========================================
  let s11 = pres.addSlide();
  s11.background = { color: C.darkBg };
  s11.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  s11.addText("谢谢聆听", {
    x: 0.8, y: 1.5, w: 8.4, h: 1.0,
    fontSize: 48, fontFace: "Arial Black", color: C.white, bold: true, align: "center", margin: 0,
  });

  s11.addShape(pres.shapes.LINE, {
    x: 3.5, y: 2.7, w: 3, h: 0,
    line: { color: C.accent, width: 2 },
  });

  s11.addText("欢迎提问 & 交流", {
    x: 0.8, y: 3.0, w: 8.4, h: 0.6,
    fontSize: 20, fontFace: "Calibri", color: C.accent, align: "center", margin: 0,
  });

  s11.addText("试试用 GPT Images 2.0 生成你的第一张 AI 图片吧！", {
    x: 0.8, y: 3.8, w: 8.4, h: 0.5,
    fontSize: 14, fontFace: "Calibri", color: C.midGray, align: "center", margin: 0,
  });

  // 保存
  await pres.writeFile({ fileName: "./GPT_Images_2.0_分享.pptx" });
  console.log("PPT 生成成功！");
}

main().catch(err => { console.error(err); process.exit(1); });