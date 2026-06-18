<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="WriteOnSide लोगो" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · Windows साइड पैनल Markdown नोट ऐप।</strong><br />
  डिस्क पर सादी फ़ाइलें। Obsidian-संगत। हमेशा स्क्रीन किनारे पर तैयार।
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 और 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.2-2ea44f" alt="संस्करण 0.1.2" />
</p>

<p align="center">
  <strong>भाषाएँ:</strong>
  <a href="../README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.nl.md">Nederlands</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.uk.md">Українська</a>
</p>

WriteOnSide (随边记) आपके चुने हुए फ़ोल्डर में Markdown नोट रखता है। कोई निजी डेटाबेस या अनिवार्य क्लाउड सेवा नहीं है, इसलिए एक ही Vault WriteOnSide, Obsidian, VS Code या किसी अन्य संपादक में खोला जा सकता है।

> [!NOTE]
> WriteOnSide `0.1.2` सक्रिय विकास में एक प्री-रिलीज़ परियोजना है। अपग्रेड से पहले महत्वपूर्ण नोट का बैकअप लें और रिलीज़ नोट पढ़ें।

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="Windows पर WriteOnSide साइड पैनल" width="720" />
</p>

## स्थापना

### Windows बिल्ड डाउनलोड करें

[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases) से नवीनतम `WriteOnSide.exe` डाउनलोड करें।

WriteOnSide वर्तमान में एकल-फ़ाइल पोर्टेबल Windows ऐप के रूप में वितरित है:

1. `WriteOnSide.exe` डाउनलोड करें।
2. उस फ़ोल्डर में रखें जहाँ ऐप रखना चाहते हैं।
3. चलाएँ और नोट फ़ोल्डर या मौजूदा Obsidian Vault चुनें।
4. पैनल दिखाने/छिपाने के लिए `Ctrl+Shift+Enter` उपयोग करें।

अहस्ताक्षरित विकास बिल्ड पर Windows SmartScreen चेतावनी दिखा सकता है। चलाने से पहले पुष्टि करें कि फ़ाइल इस रिपॉज़िटरी से है।

## मुख्य विशेषताएँ

### साइड पैनल

- बिना फ़्रेम, पूरी ऊँचाई, हमेशा ऊपर
- बाएँ या दाएँ स्क्रीन किनारे पर कॉन्फ़िगर करने योग्य लेआउट
- वैश्विक दिखाएँ/छिपाएँ शॉर्टकट, डिफ़ॉल्ट `Ctrl+Shift+Enter`
- समायोज्य पैनल चौड़ाई, फ़ाइल एक्सप्लोरर चौड़ाई और अपारदर्शिता
- खुलने, बंद होने, लेआउट और आकार बदलने में सुचारू व्यवहार
- सिस्टम ट्रे नियंत्रण और वैकल्पिक Windows स्टार्टअप
- एकल-इंस्टेंस व्यवहार और मल्टी-मॉनिटर वर्क एरिया स्थिति

### Markdown संपादन

- लाइव सिंटैक्स हाइलाइट के साथ संपादन योग्य Markdown स्रोत
- लिंक और छवियों के साथ केवल-पढ़ने योग्य रेंडर मोड
- शीर्षक, ज़ोर, उद्धरण, सूची, कार्य, तालिका, कोड, लिंक, छवि, हाइलाइट और टेक्स्ट रंग के लिए टूलबार
- शीर्षक, टैग, तिथि, उपनाम आदि के साथ YAML front matter
- खोजें और बदलें, पंक्ति संख्या, रूपरेखा और चिपके शीर्षक
- भाषा लेबल और एक-क्लिक कॉपी वाले fenced कोड ब्लॉक
- कॉन्फ़िगर करने योग्य फ़ॉन्ट, टेक्स्ट आकार, थीम और कमांड शॉर्टकट

### इंटरफ़ेस भाषाएँ

ऐप में **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी**, **Українська** शामिल हैं। **सेटिंग्स → सामान्य → भाषा** में बदलें।

### Obsidian संगतता

| सुविधा | समर्थन |
|---|---|
| विकी लिंक: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | हाँ |
| ब्लॉक संदर्भ: `[[Note#^block-id]]` | हाँ |
| नोट और छवि एम्बेड: `![[file]]` | हाँ |
| कॉलआउट: `> [!note]` | पढ़ने का मोड |
| फ़ुटनोट, `%%टिप्पणियाँ%%` और इनलाइन `#tags` | हाँ |
| कार्य सूची: `- [ ]` और `- [x]` | हाँ |
| नोट का नाम बदलें और आने वाले wikilink अपडेट करें | हाँ |

`[[` टाइप करने पर नोट पूर्णता खुलती है। संपादन मोड में `Ctrl+क्लिक` wikilink का पालन करता है। बैकलिंक टूल उन नोटों की सूची देता है जो वर्तमान नोट से जुड़े हैं।

### फ़ाइलें और अटैचमेंट

- रिकर्सिव खोज के साथ lazy-loaded फ़ाइल एक्सप्लोरर
- बहु-चयन YAML टैग फ़िल्टर
- फ़ाइल बनाएँ, नाम बदलें, हटाएँ, खींचें और पूर्वावलोकन
- Markdown और सामान्य टेक्स्ट/सोर्स कोड प्रारूप संपादित करें
- नोट में छवि चिपकाएँ या खींचें
- पोर्टेबल सापेक्ष लिंक के साथ कॉन्फ़िगर करने योग्य अटैचमेंट फ़ोल्डर
- Vault के बाहर परमाणु सहेज और टाइमस्टैम्प बैकअप
- ज़ूम और पैन के साथ छवि दर्शक

## सिस्टम आवश्यकताएँ

**अंतिम उपयोगकर्ताओं के लिए:**

- Windows 10 या Windows 11
- मानक डेस्कटॉप सत्र; Windows on ARM का अभी औपचारिक परीक्षण नहीं हुआ

**स्रोत विकास के लिए:**

- Python 3.12
- [`requirements.txt`](../requirements.txt) में सूचीबद्ध पैकेज

## स्रोत से चलाएँ

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

पहली बार चलाने पर नोट फ़ोल्डर या मौजूदा Obsidian Vault चुनें।

## मूल उपयोग

- हैमबर्गर बटन से फ़ाइल एक्सप्लोरर खोलें या बंद करें।
- टूलबार से संपादन/पढ़ने का मोड बदलें।
- टूलबार या एक्सप्लोरर से नोट बनाएँ।
- Markdown नोट में सीधे छवि चिपकाएँ ताकि वह कॉन्फ़िगर अटैचमेंट फ़ोल्डर में कॉपी हो।
- नोट फ़िल्टर करने के लिए एक्सप्लोरर के निचले भाग में YAML टैग चुनें।
- नोट फ़ोल्डर, लेआउट, चौड़ाई, अपारदर्शिता, थीम, फ़ॉन्ट, वैश्विक शॉर्टकट और टूलबार शॉर्टकट कॉन्फ़िगर करने के लिए सेटिंग्स खोलें।
- पैनल बंद करने पर ऐप छिप जाता है; वैश्विक शॉर्टकट या ट्रे मेनू से फिर दिखाएँ।

## परीक्षण

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

वर्तमान स्रोत में कॉन्फ़िगरेशन, Markdown रेंडरिंग, शॉर्टकट, स्टोरेज, नोट इंडेक्सिंग, Obsidian सिंटैक्स, wikilink नाम बदलना और अंतर्राष्ट्रीयकरण के यूनिट परीक्षण शामिल हैं।

## Windows EXE बनाएँ

रिलीज़ स्क्रिप्ट को रनटाइम निर्भरताओं के अलावा PyInstaller और PyMuPDF चाहिए:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

स्क्रिप्ट:

1. `VERSION` में पैच संस्करण बढ़ाती है।
2. SVG लोगो से PNG और ICO फ़ाइलें निर्यात करती है।
3. PyInstaller से एकल-फ़ाइल Windows executable बनाती है।
4. `dist-native-tree-vX.Y.Z\WriteOnSide.exe` में लिखती है।
5. तीन नवीनतम रिलीज़ निर्देशिकाएँ रखती है।

अतिरिक्त आदेश और समस्या निवारण के लिए [`BUILDING.md`](../BUILDING.md) देखें।

## डेटा स्थान

| डेटा | स्थान |
|---|---|
| नोट और अटैचमेंट | उपयोगकर्ता-चयनित फ़ोल्डर या Obsidian Vault |
| सेटिंग्स | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| प्रबंधित बैकअप | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide को खाते या अंतर्निहित क्लाउड सेवा की आवश्यकता नहीं। नोट तभी कंप्यूटर छोड़ते हैं जब उपयोगकर्ता Vault को अलग से कॉन्फ़िगर सिंक सेवा में रखता है।

## परियोजना संरचना

```text
writeonside.py          ऐप प्रवेश बिंदु
writeonside_app/        ऐप स्रोत कोड
assets/                 SVG, PNG और ICO संसाधन
scripts/                बिल्ड सहायक स्क्रिप्ट
tests/                  यूनिट परीक्षण
licenses/               तृतीय-पक्ष लाइसेंस पाठ
WriteOnSide.spec        PyInstaller कॉन्फ़िगरेशन
build_release.ps1       संस्करणित Windows रिलीज़ स्क्रिप्ट
BUILDING.md             विस्तृत बिल्ड निर्देश
THIRD_PARTY_NOTICES.md  निर्भरता श्रेय और लाइसेंस सूचकांक
LICENSE                 WriteOnSide स्रोत MIT लाइसेंस
```

## लाइसेंसिंग

WriteOnSide का मूल स्रोत कोड
[MIT लाइसेंस](../LICENSE) के अंतर्गत है।

तृतीय-पक्ष घटक
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) में सूचीबद्ध अपने लाइसेंस के अधीन रहते हैं।

<p align="center">
  <sub>Python | Tkinter | Markdown | Obsidian-संगत सादी फ़ाइलें</sub>
</p>
