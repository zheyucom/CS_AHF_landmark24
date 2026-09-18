const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';

// Vintage & Academic palette
const theme = {
  primary: "003049",    // deep navy blue
  secondary: "780000",  // deep red
  accent: "669bbc",     // muted blue
  light: "fdf0d5",      // cream
  bg: "FFFFFF"          // white background for clean academic look
};

for (let i = 1; i <= 18; i++) {
  const num = String(i).padStart(2, '0');
  const slideModule = require(`./slide-${num}.js`);
  slideModule.createSlide(pres, theme);
}

pres.writeFile({ fileName: './output/AHF_HD_Deterioration_Progress_Report.pptx' })
  .then(fileName => console.log(`Created: ${fileName}`));
