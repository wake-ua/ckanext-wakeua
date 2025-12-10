[![Tests](https://github.com/wake-ua/ckanext-wakeua/workflows/Tests/badge.svg?branch=main)](https://github.com/wake-ua/ckanext-wakeua/actions)

# *TDATA/ckanext-wakeua*

> CKAN extension adapted for the TDATA project

---

## Objectives

- Make aviable an extension for the TDATA project

---

## Funding Information

This research project is supported by:

- **Funding organization/institution:**  Conselleria de Educación, Universidades y Empleo de la Generalitat Valenciana
- **Program or grant:** Subvenciones a grupos de investigación consolidados
- **Project code/reference:** CIAICO/2022/019
- **Duration:** [01/01/2023 – 31/12/2025]  

---

## Technology
- Python
- CKAN

---

## Installation and Usage

### Installation

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/wake-ua/ckanext-wakeua.git
    cd ckanext-wakeua
    pip install -e .
	pip install -r requirements.txt

3. Add `wakeua` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


### Config settings

None at present


### Developer installation

To install ckanext-wakeua for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/wake-ua/ckanext-wakeua.git
    cd ckanext-wakeua
    python setup.py develop
    pip install -r dev-requirements.txt


### Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


---

## Authors / Contributors
- Lucía De Espona Pernas – [@espona](https://github.com/espona)   

---

## License

This project is distributed under the [MIT License](LICENSE).

---


## 💬 Contact

For questions, collaborations, or further information:

📧 [wake@dlsi.ua.es](mailto:wake@dlsi.ua.es)  
🌐 [Wake Research group](https://wake.dlsi.ua.es/)
