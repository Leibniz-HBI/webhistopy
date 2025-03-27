# WebHistoPy

Experimental reconceptualisation of Webhistorian as an application written in Python.

It can be adapted and build with the [Beeware framework](https://beeware.org/). Take their tutorial, which requires only basic Python skills, and you should be able to work on and with this project.

At the moment, the app has no localisations and labels and dialogues are in English (screenshots in German are outdated). Feel free to contribute localisations.

The app enables participants of a study to provide a researcher with a retracted version of their browsing history across several browsers.

Participants can:

1. provide a pseudonym (e.g. to link data with a survey)
2. choose their typical working times to filter down results
3. hide remaining domains that they want to stay private
4. inspect the data before upload
5. create some rudimentary visualisations (bar chart and network visualisation) of their data (saved as files on their desktop)

Users receive the data in form of a CSV and a YAML file on their Desktop which can be sent to the researchers.

## Installation for Users

Installers for macOS and Windows can be found under [Releases](https://github.com/Leibniz-HBI/webhistopy/releases).

But please be aware that the software is experimental and will most likely be outdated without a recent update of the code and dependencies, which means, e.g., that it might misread the respective browser databases.

Please be aware of known issues in [Issues](https://github.com/Leibniz-HBI/webhistopy/issues) and verify results before using the app for research purposes.

Please raise an issue if you need help with updating the code or creating a Linux installer.

## Screenshots

For impression purposes only. Might be outdated.

### macOS

![Screenshot 2021-09-02 at 16 44 53](https://user-images.githubusercontent.com/8951994/131865159-8679f689-e063-4af5-b990-a0ed18c04985.png)

![image](https://github.com/user-attachments/assets/99caf989-1461-41b1-ae43-9eb89db2719f)

### Windows

![Screenshot (1) (1) copy](https://user-images.githubusercontent.com/8951994/118266366-c1024400-b4ba-11eb-824a-568091013b6b.png)


## Development

All relevant code is in https://github.com/Leibniz-HBI/webhistopy/tree/main/webhistopy/src/webhistopy. The app can be configured to suit your needs in https://github.com/Leibniz-HBI/webhistopy/blob/main/webhistopy/src/webhistopy/config.yaml.

### Environment Setup

This project uses pipenv to manage dependencies. To install pipenv, follow the instructions at https://pipenv.pypa.io/en/latest/installation.html

Then run pipenv shell to activate the virtual environment and install the dependencies:

```bash
pipenv shell
pipenv install --dev
cd webhistopy
briefcase create
```

This should reproduce the environment used to develop this project. To add or update/upgrade dependencies, follow pipenv's documentation.

# Citation

If using code from this repo or the tool itself for a publication, please cite the tool itself or the paper it was developed for:

Merten, L., & Münch, F. V.,  Schuster, M. (2024). I really thought I would use more than just Google: Investigating professional journalistic online use with browser history donations. Computational Communication Research, 6(2), 1. [https://www.aup-online.com/content/journals/10.5117/CCR2024.2.7.MERT](https://www.aup-online.com/content/journals/10.5117/CCR2024.2.7.MERT)

