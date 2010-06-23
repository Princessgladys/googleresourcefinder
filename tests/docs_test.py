from selenium_test_case import SeleniumTestCase


class DocsTest(SeleniumTestCase):
    def test_links_between_pages(self):
        self.open_path('/help')
        self.assert_text_present('Frequently Asked Questions')

        self.click_and_wait('link=Terms of Service')
        self.assert_text_present('Terms of Service for Google Resource Finder')

        self.click_and_wait('link=Privacy')
        self.assert_text_present('Google Resource Finder Privacy Policy')

        self.click_and_wait('link=Help')
        self.assert_text_present('Frequently Asked Questions')

    def test_languages(self):
        # Spanish (es-419)
        self.open_path('/help?lang=es')
        self.assert_text_present('Preguntas frecuentes')

        self.click_and_wait('link=Condiciones del servicio')
        self.assert_text_present(
            'Condiciones del servicio del Buscador de recursos de Google')

        self.click_and_wait(u'link=Privacidad')
        self.assert_text_present(
            u'Pol\u00edtica de privacidad del Buscador de recursos de Google')

        self.click_and_wait(u'link=Ayuda')
        self.assert_text_present('Preguntas frecuentes')

        # French (fr)
        self.open_path('/help?lang=fr')
        self.assert_text_present(u'Questions fr\u00e9quentes')

        self.click_and_wait('link=Conditions d\'utilisation')
        self.assert_text_present(
            u'Conditions d\'utilisation de Google Resource Finder')

        self.click_and_wait(u'link=Confidentialit\u00e9')
        self.assert_text_present(
            u'R\u00e8gles de confidentialit\u00e9 de Google Resource Finder')

        self.click_and_wait(u'link=Aide')
        self.assert_text_present(u'Questions fr\u00e9quentes')

        # Kreyol (ht)
        self.open_path('/help?lang=ht')
        self.assert_text_present(u'Kesyon Div\u00e8s Moun Poze Tout Tan')

        self.click_and_wait(u'link=Kondisyon S\u00e8vis yo')
        self.assert_text_present(
            u'Kondisyon S\u00e8vis pou Resource Finder Google')

        self.click_and_wait(u'link=Vi prive')
        self.assert_text_present(
            u'Politik Resp\u00e8 Pou Moun ak \u201cResource Finder\u201d nan Google')

        self.click_and_wait(u'link=Ed')
        self.assert_text_present(u'Kesyon Div\u00e8s Moun Poze Tout Tan')
