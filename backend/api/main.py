import io
import base64

app = Flask(__name__)
CORS(app)

def get_date(string_date):
    return dateutil.parser.isoparse(string_date)

@app.route('/predict', methods=['POST'])
def predict():
    params = request.get_json()
    model = Model.find_one({ "type": params["model"]  }, sort=[( '_id', pymongo.DESCENDING )])
    clf = load('models/' + str(model["_id"]))
    sentences = params["sentences"]
    pst = PorterStemmer()
    lemma_sentences = [[pst.stem(token) for token in word_tokenize(sentence.lower())] for sentence in sentences]
    most_freq = Attribute.find({}, sort=[( 'id', pymongo.ASCENDING )])
    most_freq = [word["value"] for word in most_freq]
    X = words_presences(most_freq, lemma_sentences)
    predicted = clf.predict(X)
    result = list(zip(sentences, predicted))
    result = [{ "sentence": x[0], "prediction": int(x[1]) } for x in result]
    return jsonify(result)

@app.route('/train', methods=['POST'])
def train():
    sentences = Sentence.find({})
    sentences = [sentence for sentence in sentences]
    pst = PorterStemmer()
    lemma_sentences = [[pst.stem(token) for token in word_tokenize(sentence["text"].lower())] for sentence in sentences]
    most_freq = most_common_keywords_with_freq(lemma_sentences, 500)
    Attribute.delete_many({})
    Attribute.insert_many([{ "id": word[0],"value": word[1][0], "count": word[1][1] } for word in enumerate(most_freq)])
    most_freq = [x[0] for x in most_freq]
    X_presences_common = words_presences(most_freq, lemma_sentences)
    y = [sentence["class"] for sentence in sentences]

    clf = svm.SVC(kernel='linear', C=1)
    scores = cross_val_score(clf, X_presences_common, y, cv=10)
    y_pred = cross_val_predict(clf, X_presences_common, y, cv=10)
    clf = clf.fit(X_presences_common, y)
    conf_mat = confusion_matrix(y, clf.predict(X_presences_common))
    svmDocument = { "type": "svm", "accuracy": scores.mean(), "std": scores.std(), "confusion_matrix": conf_mat.tolist() }
    dump(clf, 'models/' + str(Model.insert_one(svmDocument).inserted_id))
    del svmDocument["_id"]

    clf = knn(n_neighbors=3, metric='minkowski')
    scores = cross_val_score(clf, X_presences_common, y, cv=10)
    y_pred = cross_val_predict(clf, X_presences_common, y, cv=10)
    clf = clf.fit(X_presences_common, y)
    conf_mat = confusion_matrix(y, clf.predict(X_presences_common))
    knnDocument = { "type": "knn", "accuracy": scores.mean(), "std": scores.std(), "confusion_matrix": conf_mat.tolist() }
    dump(clf, 'models/' + str(Model.insert_one(knnDocument).inserted_id))
    del knnDocument["_id"]

    clf = lr()
    scores = cross_val_score(clf, X_presences_common, y, cv=10)
    y_pred = cross_val_predict(clf, X_presences_common, y, cv=10)
    clf = clf.fit(X_presences_common, y)
    conf_mat = confusion_matrix(y, clf.predict(X_presences_common))
    logisticDocument = { "type": "logistic", "accuracy": scores.mean(), "std": scores.std(), "confusion_matrix": conf_mat.tolist() }
    dump(clf, 'models/' + str(Model.insert_one(logisticDocument).inserted_id))
    del logisticDocument["_id"]

    return jsonify({ "svm": svmDocument, "knn": knnDocument, "logistic": logisticDocument })

@app.route('/cluster', methods=['POST'])
def cluster():
    threshold = request.get_json()["threshold"]
    pipeline = [
        { '$group': { '_id': '$document_id', 'sentences': { '$push': '$text' } } },
        { '$project': { '_id': 1, 'text': { '$reduce': { 'input': '$sentences', 'initialValue': '', 'in': { '$concat': ['$$value', ' ', '$$this'] } } } } }
    ]
    document = list(Sentence.aggregate(pipeline))
    texts = [sentence["text"] for sentence in document]
    pst = PorterStemmer()
    stemmed_texts = [[pst.stem(token) for token in word_tokenize(text.lower())] for text in texts]

    most_freq = most_common_keywords(stemmed_texts, 300)

    X_presences_common = words_presences(most_freq, stemmed_texts)
    # “complete”, “average”, “single”
    model = AgglomerativeClustering(distance_threshold=threshold, n_clusters=None, linkage="complete")

    model = model.fit(X_presences_common)
    result = list(zip(texts, model.labels_))
    result = [{ "text": x[0], "cluster": int(x[1]) } for x in result]
    plt.title('Hierarchical Clustering Dendrogram')
    # plot the top three levels of the dendrogram
    plot_dendrogram(model, p=3, get_leaves=True)
    plt.xlabel("Number of points in node (or index of point if no parenthesis).")
    stringBytes = io.BytesIO()
    plt.savefig(stringBytes, format='png')
    stringBytes.seek(0)
    base64Representation = base64.b64encode(stringBytes.read())
    encodedStr = str(base64Representation, "utf-8")
    return dumps({ "result": result, "image": encodedStr })


@app.route('/acquisition', methods=['POST', 'GET'], defaults={'acquisition_id': None})
@app.route('/acquisition/<acquisition_id>', methods=['POST', 'GET'])
def acquisition(acquisition_id):
    if request.method == 'POST':
        acquisition = request.get_json()
        document = {
            "annuncement_date" : get_date(acquisition["annuncement_date"]),
            "signing_date": get_date(acquisition["signing_date"]),
            "status": acquisition["status"].lower().strip(),
            "acquiror": {
                "name": acquisition["acquiror"]["name"],
                "ticker": acquisition["acquiror"]["ticker"].lower().strip(),
                "state": acquisition["acquiror"]["state"].lower().strip(),
            },
            "target": {
                "name": acquisition["target"]["name"],
                "ticker": acquisition["target"]["ticker"].lower().strip(),
                "state": acquisition["target"]["state"].lower().strip()
            },
            "documents": []
        }
        return {"_id": str(Acquisition.insert_one(document).inserted_id) }
    if acquisition_id is not None:
        acquisition = Acquisition.find_one({ '_id': ObjectId(acquisition_id) })
        return dumps(acquisition)
    acquisition = Acquisition.find()
    return dumps(acquisition)


@app.route('/document', methods=['POST'])
def document():
    documents = request.get_json()
    acquisition_id = documents["acquisition_id"]
    d = {
        "title": documents["title"],
        "link": documents["link"],
        "date": get_date(documents["date"]),
        "source": documents["source"],
        "type": documents["type"],
        "_id": ObjectId()
    }
    return { 'updated': Acquisition.update_one({ "_id": ObjectId(acquisition_id) }, { '$push': {'documents': d} }).modified_count > 0 }

@app.route('/sentence', methods=['POST', 'GET'], defaults={'sentence_id': None})
@app.route('/sentence/<sentence_id>', methods=['POST', 'GET'])
def sentence(sentence_id):
    if request.method == 'POST':
        sentences = request.get_json()
        if sentences["type"] == 'twitter':
            sentences = [{ "text": sentence["text"], "class": sentence["class"], "type": sentences["type"]} for sentence in sentences["sentences"]]
        else:
            sentences = [{"text": sentence["text"], "class": sentence["class"], "type": sentences["type"], "document_id": ObjectId(sentences["document_id"])} for sentence in sentences["sentences"]]
            pipeline = [
                { '$unwind': '$documents' },
                { '$match': { 'documents._id': sentences["document_id"] } }
            ]
            document = list(Acquisition.aggregate(pipeline))
            if len(document) != 1:
                abort(400) # Document not found
        Sentence.insert_many(sentences)
        return dumps({ 'inserted': True })

    document_id = request.args.get('document_id')
    if sentence_id is not None:
        return dumps(Sentence.find_one({ '_id': ObjectId(sentence_id) }))

    if document_id is not None:
        return dumps(Sentence.find({ 'document_id': ObjectId(document_id) }))

    return dumps(Sentence.find({}))

@app.route('/keyword', methods=['POST', 'GET'])
def keyword():
    if request.method == 'POST':
        keyword = request.get_json()
        Keyword.delete_many({})
        return dumps(Keyword.insert_many(keyword).inserted_ids)

    type = request.args.get('type')
    if type is not None:
        return dumps(Keyword.find({ 'type': type }))
    return dumps(Keyword.find({ }))

@app.route('/tweets/<username>', methods=['GET'])
def tweets(username):
    tweetCriteria = None
    if request.args.get('since') is not None and request.args.get('until') is not None:
        tweetCriteria = got.manager.TweetCriteria().setUsername(username).setMaxTweets(50).setSince(request.args.get('since')).setUntil(request.args.get('until'))
    elif request.args.get('since') is not None:
        tweetCriteria = got.manager.TweetCriteria().setUsername(username).setMaxTweets(50).setSince(request.args.get('since'))
    else:
        tweetCriteria = got.manager.TweetCriteria().setUsername(username).setMaxTweets(50)
    tweets = got.manager.TweetManager.getTweets(tweetCriteria)
    tweets = [tweet.text for tweet in tweets]
    return jsonify({"tweets": tweets})
