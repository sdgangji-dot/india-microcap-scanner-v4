function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('India MF Institutional Accumulation & Value Research Scanner')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
