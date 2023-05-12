# WebHistoPy

Experimental reconceptualisation of Webhistorian as an application written in Python.

It can be adapted and build with the [Beeware framework](https://beeware.org/). Take their tutorial, which requires only basic Python skills, and you should be able to work on and with this project.

At the moment, the app has no localisation and labels and dialogues are in German as it was UX-tested with German participants. Feel free to contribute localisations.

The app enables participants of a study to provide a researcher with a retracted version of their browsing history across several browsers.

Participants can:

1. provide a pseudonym (e.g. to link data with a survey)
2. choose their typical working times to filter down results
3. hide remaining domains that they want to stay private
4. inspect the data before upload
5. receive a copy of their data on upload

Researchers receive the data in form of a CSV and a YAML file in a [Nextcloud drop folder](https://nextcloud.com/file-drop/) of their choice.

## Screenshots

For impression purposes only. Might be outdated.

### macOS

![Screenshot 2021-09-02 at 16 44 53](https://user-images.githubusercontent.com/8951994/131865159-8679f689-e063-4af5-b990-a0ed18c04985.png)

### Windows

![Screenshot (1) (1) copy](https://user-images.githubusercontent.com/8951994/118266366-c1024400-b4ba-11eb-824a-568091013b6b.png)


## Development

All relevant code is in https://github.com/Leibniz-HBI/webhistopy/tree/main/webhistopy/src/webhistopy. The app can be configured to suit your needs in https://github.com/Leibniz-HBI/webhistopy/blob/main/webhistopy/src/webhistopy/config.yaml.
