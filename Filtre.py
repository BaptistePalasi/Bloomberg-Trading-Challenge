import blpapi

options = blpapi.SessionOptions()
options.setServerHost('localhost')
options.setServerPort(8194)
session = blpapi.Session(options)

if not session.start():
    print("Échec du démarrage de la session Bloomberg.")
elif not session.openService("//blp/refdata"):
    print("Impossible d'ouvrir le service //blp/refdata.")
else:
    print("Connexion locale réussie !")
    refDataService = session.getService("//blp/refdata")
    request = refDataService.createRequest("ReferenceDataRequest")
    
    # Remplacer par le ticker exact testé
    request.getElement("securities").appendValue("WORLD Index")
    request.getElement("fields").appendValue("INDX_MEMBERS")
    
    # Ajout de l'override date
    overrides = request.getElement("overrides")
    override = overrides.appendElement()
    override.setElement("fieldId", "END_DATE_OVERRIDE")
    override.setElement("value", "20261009")

    session.sendRequest(request)

    # Récupération de la réponse brute
    while True:
        ev = session.nextEvent(500)
        for msg in ev:
            print(msg)
        if ev.eventType() == blpapi.Event.RESPONSE:
            break