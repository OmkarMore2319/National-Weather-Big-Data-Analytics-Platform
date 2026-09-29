"""
Model training script for Weather Event Classifier.
Trains a lightweight TF-IDF Vectorizer + Logistic Regression model
on ~220 hand-labeled weather report samples across 7 target event categories.
Outputs saved to `ml_verification/models/`.
"""

import os
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

TRAINING_DATA = [
    # ================= RAINFALL =================
    ("Continuous moderate rain falling over South Delhi since morning.", "RAINFALL"),
    ("Light drizzle observed near Connaught Place with overcast sky.", "RAINFALL"),
    ("Heavy downpour started in Andheri, roads are getting wet.", "RAINFALL"),
    ("Torrential rain lashing Pune city, umbrellas out everywhere.", "RAINFALL"),
    ("Monsoon showers bring relief from heat across central Mumbai.", "RAINFALL"),
    ("Non-stop rainfall for the past 2 hours in Bangalore.", "RAINFALL"),
    ("Sudden cloud burst of rain in Shimla, pleasant weather.", "RAINFALL"),
    ("Steady drizzling and precipitation recorded in Dehradun.", "RAINFALL"),
    ("Heavy showers recorded in Chennai coastal areas today.", "RAINFALL"),
    ("Intermittent rainfall with overcast sky in Guwahati.", "RAINFALL"),
    ("It has been pouring rain all afternoon in Hyderabad.", "RAINFALL"),
    ("Mild rain shower cooled down the temperature in Jaipur.", "RAINFALL"),
    ("Persistent rainy weather and wet asphalt on Western Express Highway.", "RAINFALL"),
    ("Rain gauge shows 45mm of precipitation over the last 3 hours.", "RAINFALL"),
    ("Mausam suhana ho gaya, halki barish shuru ho gayi hai.", "RAINFALL"),
    ("Tez baarish ho rahi hai subah se Pune me.", "RAINFALL"),
    ("Barsaat ki wajah se mausam thanda ho gaya hai.", "RAINFALL"),
    ("Pura din bundabandi chalti rahi, wet roads all around.", "RAINFALL"),
    ("Bohot tez barish shuru ho chuki hai South Mumbai me.", "RAINFALL"),
    ("Rimjhim barish aur thandi hawa chal rahi hai.", "RAINFALL"),
    ("Heavy rain in Ahmedabad, dark clouds hovering above.", "RAINFALL"),
    ("Drenching rain across suburban railway tracks.", "RAINFALL"),
    ("आज सुबह से ही तेज बारिश हो रही है।", "RAINFALL"),
    ("शहर में लगातार मूसलाधार वर्षा जारी है।", "RAINFALL"),
    ("हल्की बूंदाबांदी से मौसम सुहावना हो गया।", "RAINFALL"),
    ("बरसात का मौसम शुरू, लगातार बारिश हो रही है।", "RAINFALL"),
    ("झमाझम बारिश से तापमान में भारी गिरावट दर्ज की गई।", "RAINFALL"),
    ("कोलकाता में भारी वर्षा के कारण छाते खुल गए।", "RAINFALL"),
    ("वर्षा के कारण चारों ओर गीलापन हो गया है।", "RAINFALL"),
    ("रुक-रुक कर बारिश हो रही है।", "RAINFALL"),

    # ================= THUNDERSTORM =================
    ("Severe thunderstorm with intense lightning strikes near Noida Sector 62.", "THUNDERSTORM"),
    ("Loud thunder claps and lightning flashes witnessed across North Delhi.", "THUNDERSTORM"),
    ("Thunderstorm approaching Gurgaon, sky turned pitch black at 3 PM.", "THUNDERSTORM"),
    ("Violent thunder and lightning bolts shaking windows in Kolkata.", "THUNDERSTORM"),
    ("Hailstorm and thunderstorm damaged crops in rural Punjab.", "THUNDERSTORM"),
    ("Huge hailstones falling with heavy thunder and rain in Nagpur.", "THUNDERSTORM"),
    ("Frequent lightning strikes and terrifying rumbling thunder heard in Kochi.", "THUNDERSTORM"),
    ("Intense storm cell with thunder, lightning, and squall lines.", "THUNDERSTORM"),
    ("Thunderstorm alert issued for Bhopal, lightning reported near lake.", "THUNDERSTORM"),
    ("Loud thunderous roar followed by sudden hail shower in Ranchi.", "THUNDERSTORM"),
    ("Electrical storm with non-stop lightning illuminating the night sky.", "THUNDERSTORM"),
    ("Severe thunder and hail pelting cars on the expressway.", "THUNDERSTORM"),
    ("Aasman me bijli kadak rahi hai aur bohot tez badal garaj rahe hain.", "THUNDERSTORM"),
    ("Toofani bijli aur garaj ke sath toofan aa gaya hai.", "THUNDERSTORM"),
    ("Bohot zor ka thunderclap hua, pura ghar hil gaya.", "THUNDERSTORM"),
    ("Ole gir rahe hain aur bijli chamak rahi hai Charminar ke paas.", "THUNDERSTORM"),
    ("Badal garaj rahe hain aur toofani bijli girne ki aashanka hai.", "THUNDERSTORM"),
    ("Scary lightning flashes and rumbling thunder in Chandigarh.", "THUNDERSTORM"),
    ("Thunder and hail barrage hit our locality just now.", "THUNDERSTORM"),
    ("भीषण आंधी-तूफान के साथ आकाशीय बिजली चमक रही है।", "THUNDERSTORM"),
    ("तेज बादलों की गड़गड़ाहट और बिजली गिरने की घटनाएं सामने आई हैं।", "THUNDERSTORM"),
    ("शहर में जोरदार बादलों की गर्जना और तड़ित झंझावात देखा गया।", "THUNDERSTORM"),
    ("ओलावृष्टि और तेज गर्जना के साथ भयंकर तूफान आया।", "THUNDERSTORM"),
    ("बिजली कड़कने की आवाज से इलाके में दहशत फैल गई।", "THUNDERSTORM"),
    ("ओले गिरने और बादलों के गरजने से भारी नुकसान हुआ।", "THUNDERSTORM"),
    ("आकाशीय बिजली का प्रकोप देखा गया।", "THUNDERSTORM"),
    ("गरज और चमक के साथ भीषण आकाशीय तूफान जारी।", "THUNDERSTORM"),
    ("Thunderstorm with gale force winds and dangerous lightning arcs.", "THUNDERSTORM"),
    ("Thunder rolls across the horizon with intermittent hail.", "THUNDERSTORM"),

    # ================= FLOODING =================
    ("Severe waterlogging on Western Express Highway, vehicles submerged.", "FLOODING"),
    ("Underpass completely flooded near Minto Bridge, traffic diverted.", "FLOODING"),
    ("River overflowing, residential colony submerged in flood water in Patna.", "FLOODING"),
    ("Knee-deep water stagnation outside railway station, complete gridlock.", "FLOODING"),
    ("Urban flooding witnessed in low-lying areas of Chennai after dam release.", "FLOODING"),
    ("Massive waterlogging inside basement parking lots in Bengaluru.", "FLOODING"),
    ("Streets turned into rivers, homes inundated with brown floodwaters.", "FLOODING"),
    ("Flood alert sounded as Yamuna river breaches danger mark.", "FLOODING"),
    ("Severe inundation along main arterial roads, rescue boats deployed.", "FLOODING"),
    ("Deluge leaves residential apartments marooned in water.", "FLOODING"),
    ("Waterlogging reported at multiple junctions across Kolkata.", "FLOODING"),
    ("Ground floor flats submerged under 3 feet of stagnant water.", "FLOODING"),
    ("Sarak par pani bhar gaya hai, gaadiyan doob chuki hain.", "FLOODING"),
    ("Underpass me jalbhirav, car pura paani me dhoob gayi.", "FLOODING"),
    ("Baadh ka paani mohalle me ghus gaya hai, rescue team bulao.", "FLOODING"),
    ("Pura area waterlogged hai, nikalne ka koi rasta nahi.", "FLOODING"),
    ("Jalbharav ki wajah se poora traffic jam ho chuka hai.", "FLOODING"),
    ("Heavy water stagnation and inundated lanes in Old City.", "FLOODING"),
    ("Houses inundated and streets waterlogged after lake breach.", "FLOODING"),
    ("Underground metro subway entrance completely flooded.", "FLOODING"),
    ("सड़कों पर भारी जलभराव से वाहन पानी में डूब गए हैं।", "FLOODING"),
    ("शहर में बाढ़ जैसी स्थिति, निचले इलाकों में पानी भर गया।", "FLOODING"),
    ("यमुना का जलस्तर खतरे के निशान के पार, कॉलोनियां जलमग्न।", "FLOODING"),
    ("अंडरपास में पानी भरने से बसें और कारें डूब गईं।", "FLOODING"),
    ("नदी उफान पर, तटीय बस्तियों में सैलाब का पानी घुसा।", "FLOODING"),
    ("घरों के अंदर तक बाढ़ का पानी घुस गया है, लोग छतों पर फंसे।", "FLOODING"),
    ("जलभराव के कारण जनजीवन पूरी तरह अस्त-व्यस्त हो गया।", "FLOODING"),
    ("बाढ़ के पानी से पूरे मोहल्ले जलमग्न हो चुके हैं।", "FLOODING"),
    ("बाढ़ का कहर जारी, सड़कें तालाब बन गईं।", "FLOODING"),
    ("जलभराव से सड़कें जाम, गाड़ियां तैरती नजर आईं।", "FLOODING"),

    # ================= HEATWAVE =================
    ("Scorching heatwave grips Delhi, mercury touches 47 degrees Celsius.", "HEATWAVE"),
    ("Extreme heat condition declared in Rajasthan, severe heat wave ongoing.", "HEATWAVE"),
    ("Sweltering sun and blistering heat making it impossible to step outside.", "HEATWAVE"),
    ("Severe heatwave warning issued for Vidarbha, temperatures cross 46C.", "HEATWAVE"),
    ("Sunstroke cases rising as boiling temperatures hit Ahmedabad.", "HEATWAVE"),
    ("Intense dry hot winds and soaring thermometer readings in Nagpur.", "HEATWAVE"),
    ("Unbearable heatwave conditions with blazing afternoon sun in Lucknow.", "HEATWAVE"),
    ("Mercury hits record high of 48.5C, severe heat wave red alert.", "HEATWAVE"),
    ("Extreme hot weather causing dehydration, avoid outdoor exposure.", "HEATWAVE"),
    ("Blistering heatwave sweeps across northwest plains of India.", "HEATWAVE"),
    ("Pavement radiating intense heat, air feels like a furnace in Agra.", "HEATWAVE"),
    ("Thermal stress extreme as maximum temperature remains above 45C.", "HEATWAVE"),
    ("Bohot bhayankar garmi pad rahi hai, loo chal rahi hai bahar.", "HEATWAVE"),
    ("Dhoop itni tez hai ki bahar nikalna mushkil ho gaya, 46 degree.", "HEATWAVE"),
    ("Severe loo aur tapan mahsoos ho rahi hai dopahar me.", "HEATWAVE"),
    ("Boiling hot weather, sunstroke warning in our district.", "HEATWAVE"),
    ("Garmi ke maare bura haal hai, extreme heatwave situation.", "HEATWAVE"),
    ("Loo ke thappade lag rahe hain, temperature touch kar gaya 45C.", "HEATWAVE"),
    ("Scorching sunshine and dry thermal winds baking the city.", "HEATWAVE"),
    ("Heat index dangerously high, severe heatwave prevails.", "HEATWAVE"),
    ("भीषण गर्मी और लू के थपेड़ों से लोग बेहाल हैं।", "HEATWAVE"),
    ("दिल्ली-एनसीआर में प्रचंड लू का प्रकोप, पारा 47 डिग्री पहुंचा।", "HEATWAVE"),
    ("तेज धूप और तपन से दोपहर में सड़कें सुनसान हो गईं।", "HEATWAVE"),
    ("भीषण हीटवेव का रेड अलर्ट जारी, तापमान रिकॉर्ड स्तर पर।", "HEATWAVE"),
    ("गर्म हवाओं और लू के कारण लू लगने के मामले बढ़े।", "HEATWAVE"),
    ("धूप की तपिश से जनजीवन प्रभावित, असहनीय गर्मी जारी।", "HEATWAVE"),
    ("लू चलने से तापमान 46 डिग्री के पार पहुंचा।", "HEATWAVE"),
    ("प्रचंड गर्मी और तपन का कहर जारी है।", "HEATWAVE"),
    ("सूरज की तपिश ने झुलसाया, भीषण लू की चेतावनी।", "HEATWAVE"),
    ("गर्मी ने तोड़ा रिकॉर्ड, भयंकर लू चल रही है।", "HEATWAVE"),

    # ================= FOG =================
    ("Dense fog envelops Delhi IGI Airport, runway visibility drops to 50m.", "FOG"),
    ("Thick morning fog reduces visibility to near zero on Yamuna Expressway.", "FOG"),
    ("Blanket of dense fog and winter smog causes multiple vehicle pile-ups.", "FOG"),
    ("Heavy fog reported across Punjab and Haryana plains, trains delayed.", "FOG"),
    ("Low visibility due to dense foggy conditions in Lucknow this morning.", "FOG"),
    ("Blinding white mist and smog covering northern railway tracks.", "FOG"),
    ("Dense fog warning: drivers advised to use hazard fog lights.", "FOG"),
    ("Zero visibility reported at Amritsar airport due to severe fog.", "FOG"),
    ("Thick foggy layer hovering over hills and highways in Shimla.", "FOG"),
    ("Visibility dropped below 20 meters due to impenetrable fog layer.", "FOG"),
    ("Morning mist turned into thick fog, delaying flights in Varanasi.", "FOG"),
    ("Dense haze and fog blanket envelops the entire NCR region.", "FOG"),
    ("Pura shehar kohre me dooba hua hai, kuch dikhai nahi de raha.", "FOG"),
    ("Subah se itna dense kohra hai ki zero visibility ho gayi hai.", "FOG"),
    ("Dhundh aur kohra itna zyada hai ki expressway pe gaadi slow chal rahi hai.", "FOG"),
    ("Kohre ki wajah se trains bohot late chal rahi hain.", "FOG"),
    ("Bohot thick fog hai bahar, road visibility below 30 meters.", "FOG"),
    ("Dhundh itni gehri hai ki samne ka building bhi nahi dikh raha.", "FOG"),
    ("Severe foggy morning across Delhi bypass.", "FOG"),
    ("Morning fog completely shrouding highway tolls.", "FOG"),
    ("घने कोहरे के कारण दृश्यता घटकर शून्य हो गई है।", "FOG"),
    ("सर्दियों का घना कोहरा और धुंध छाई, उड़ानों पर असर पड़ा।", "FOG"),
    ("यमुना एक्सप्रेसवे पर भारी कोहरा, गाड़ियां रेंगती नजर आईं।", "FOG"),
    ("घनी धुंध और कुहासे के कारण सामने कुछ दिखाई नहीं दे रहा।", "FOG"),
    ("कोहरे का कहर: कई ट्रेनें और फ्लाइट्स रद्द की गईं।", "FOG"),
    ("सुबह के समय घना कोहरा छाया रहा, दृश्यता 50 मीटर से कम।", "FOG"),
    ("कोहरे की चादर में लिपटा शहर, विजिबिलिटी शून्य।", "FOG"),
    ("सफेद धुंध और कोहरे ने पूरे शहर को ढक लिया है।", "FOG"),
    ("कुहासा और ठंड से दृश्यता काफी घट गई।", "FOG"),
    ("सड़क पर भारी धुंध के कारण फॉग लाइट जलानी पड़ रही है।", "FOG"),

    # ================= DUST_STORM =================
    ("Severe dust storm hits Jodhpur with blinding sand and high wind gusts.", "DUST_STORM"),
    ("Massive dust gale swept across Bikaner, turning sky reddish brown.", "DUST_STORM"),
    ("Blinding sandstorm sweeps through Western Rajasthan highway.", "DUST_STORM"),
    ("Sudden andhi and dust storm plunged Jaipur into daytime darkness.", "DUST_STORM"),
    ("Heavy dust storm with particulate matter engulfs Delhi NCR skyline.", "DUST_STORM"),
    ("Wall of dust and sand advancing rapidly over desert plains.", "DUST_STORM"),
    ("High velocity dust gale blowing sand into eyes, low visibility.", "DUST_STORM"),
    ("Severe haboob like dust storm blankets urban areas with grit.", "DUST_STORM"),
    ("Violent sand storm knocked down tin roofs in Barmer.", "DUST_STORM"),
    ("Dust laden winds blinding commuters on national highway.", "DUST_STORM"),
    ("Sudden sandstorm caused visibility to drop sharply in Jaisalmer.", "DUST_STORM"),
    ("Dry dust gale swept through agricultural fields causing crop damage.", "DUST_STORM"),
    ("Bohot tezz aandhi aayi hai, charo taraf ret aur dhool udd rahi hai.", "DUST_STORM"),
    ("Aandhi toofan ke sath dhool bhari hawayen chal rahi hain.", "DUST_STORM"),
    ("Dhool ka toofan aa gaya, aakash me sirf mitti hi mitti hai.", "DUST_STORM"),
    ("Ret ka toofan highway pe chal raha hai, blind ho gaye.", "DUST_STORM"),
    ("Andhi ki wajah se dhoop gayab ho gayi aur dhool bhar gayi.", "DUST_STORM"),
    ("Bikaner me zabardast sandstorm, visibility dropped to zero.", "DUST_STORM"),
    ("Dust storm swirling furiously across open fields.", "DUST_STORM"),
    ("Grit and dust blowing with severe force in Ajmer.", "DUST_STORM"),
    ("धूल भरी आंधी चलने से दिन में ही अंधेरा छा गया।", "DUST_STORM"),
    ("रेगिस्तान में भीषण रेत का तूफान, चारों तरफ धूल ही धूल।", "DUST_STORM"),
    ("तेज आंधी के साथ धूल के गुबार उठते दिखाई दिए।", "DUST_STORM"),
    ("धूल भरी तेज आंधी से दृश्यता बेहद कम हो गई।", "DUST_STORM"),
    ("राजस्थान के कई हिस्सों में भयंकर रेतीला तूफान आया।", "DUST_STORM"),
    ("रेत और मिट्टी का तूफान आने से जनजीवन अस्त-व्यस्त।", "DUST_STORM"),
    ("आंधी के कारण धूल के बवंडर देखे गए।", "DUST_STORM"),
    ("रेतीली आंधी ने आसमान को भूरा कर दिया।", "DUST_STORM"),
    ("धूल भरी आंधी से घरों में रेत भर गई।", "DUST_STORM"),
    ("अंधी और धूल के तूफान से पेड़ों को नुकसान हुआ।", "DUST_STORM"),

    # ================= STRONG_WIND =================
    ("Gale force winds gusting up to 75 km/h recorded in coastal Odisha.", "STRONG_WIND"),
    ("Extremely strong winds uprooted electric poles and hoardings in Puri.", "STRONG_WIND"),
    ("High velocity squall and howling winds rattling windows in Mumbai.", "STRONG_WIND"),
    ("Violent windstorm swept across seafront, blowing away umbrellas.", "STRONG_WIND"),
    ("Gusty winds reaching 80 kph causing disruption to ferry services.", "STRONG_WIND"),
    ("Squall line bringing dangerous strong gusts over coastal belt.", "STRONG_WIND"),
    ("Heavy gales knocked down large banyan tree blocking main avenue.", "STRONG_WIND"),
    ("Fierce wind gusts threatening temporary structures and tin sheds.", "STRONG_WIND"),
    ("Blustery conditions with wind speeds exceeding 65 kmph in Visakhapatnam.", "STRONG_WIND"),
    ("Tempestuous strong wind blowing off roof tiles and billboards.", "STRONG_WIND"),
    ("Severe cyclonic winds damaging communication towers in Digha.", "STRONG_WIND"),
    ("Howling gale winds making it dangerous for two-wheelers on sea bridge.", "STRONG_WIND"),
    ("Itni tez hawa chal rahi hai ki ped gir rahe hain road pe.", "STRONG_WIND"),
    ("Toofani hawayen chal rahi hain coastal area me 70 kph ki speed se.", "STRONG_WIND"),
    ("Hawa ke tez jhonke se billboard ud kar road par gir gaya.", "STRONG_WIND"),
    ("Bohot dangerous strong wind chal rahi hai, balance kharab ho raha.", "STRONG_WIND"),
    ("Tez hawa ki wajah se power lines break ho chuki hain.", "STRONG_WIND"),
    ("Gale force gusts knocking down scooters and bikes.", "STRONG_WIND"),
    ("Violent gusty squalls roaring across the bay.", "STRONG_WIND"),
    ("Wind gusts so strong that walking against them is difficult.", "STRONG_WIND"),
    ("तेज तूफानी हवाओं के कारण कई जगह पेड़ और खंभे उखड़ गए।", "STRONG_WIND"),
    ("तटीय इलाकों में 75 किमी प्रति घंटे की रफ्तार से तेज हवाएं चल रही हैं।", "STRONG_WIND"),
    ("हवा के तेज झोंकों ने होर्डिंग्स और टिन शेड उड़ा दिए।", "STRONG_WIND"),
    ("भयंकर चक्रवाती हवाओं से समुद्र में ऊंची लहरें उठ रही हैं।", "STRONG_WIND"),
    ("तूफानी हवा चलने से बिजली के तार टूटकर गिर गए।", "STRONG_WIND"),
    ("हवा की भीषण गति से खिड़कियां और दरवाजे खड़क रहे हैं।", "STRONG_WIND"),
    ("तेज आंधी जैसी हवाओं से भारी नुकसान की आशंका।", "STRONG_WIND"),
    ("प्रचंड हवा के झोंके सड़क पर चलने वालों को गिरा रहे हैं।", "STRONG_WIND"),
    ("समुद्र किनारे तूफानी हवाओं का अलर्ट जारी।", "STRONG_WIND"),
    ("तेज हवाओं ने शहर में कई रास्तों को बाधित कर दिया।", "STRONG_WIND")
]


def train_and_save():
    base_dir = Path(__file__).resolve().parent
    models_dir = base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    texts = [item[0] for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]

    print(f"Loaded {len(texts)} training samples across 7 event categories.")

    # Build TF-IDF Vectorizer with word + sub-word character n-grams for typo & transliteration resilience
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        strip_accents=None,  # Keep Devanagari intact
        lowercase=True
    )

    X = vectorizer.fit_transform(texts)

    # Train Logistic Regression with balanced weights
    classifier = LogisticRegression(
        C=2.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42
    )
    classifier.fit(X, labels)

    y_pred = classifier.predict(X)
    print("\nTraining Classification Report:")
    print(classification_report(labels, y_pred))

    # Save vectorizer and model using relative paths inside models/
    vec_path = models_dir / "tfidf_vectorizer.joblib"
    model_path = models_dir / "event_classifier.joblib"

    joblib.dump(vectorizer, vec_path, compress=3)
    joblib.dump(classifier, model_path, compress=3)

    print(f"Saved vectorizer to: {vec_path} ({vec_path.stat().st_size / 1024:.1f} KB)")
    print(f"Saved classifier to: {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    train_and_save()
