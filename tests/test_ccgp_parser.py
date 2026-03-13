import unittest

from scraper.ccgp_parser import CCGPAnnouncementParser


class CCGPAnnouncementParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = CCGPAnnouncementParser()

    def test_parse_and_format_extract_core_ccgp_fields(self):
        html = """
        <html>
          <head>
            <meta name="ArticleTitle" content="测试中标公告" />
            <meta name="PubDate" content="2026-03-13" />
          </head>
          <body>
            <div class="vF_detail_content">
              <p>一、项目基本情况</p>
              <p>项目名称：智能项目</p>
              <p>中标（成交）信息</p>
              <p>供应商名称：测试供应商</p>
              <p>评审专家：专家甲、专家乙</p>
              <p>凡对本次公告内容提出询问，请按以下方式联系。</p>
              <p>1.采购人信息</p>
              <p>名 称：测试采购单位</p>
              <p>联系方式：张三 010-88888888</p>
              <p>2.采购代理机构信息</p>
              <p>名 称：测试代理机构</p>
              <p>联系方式：李四16620120513、王五15800204406</p>
              <p>3.项目联系方式</p>
              <p>项目联系人：赵六</p>
              <p>电 话：010-66666666</p>
            </div>
          </body>
        </html>
        """

        parsed = self.parser.parse(html, "https://www.ccgp.gov.cn/cggg/test.htm")
        formatted = self.parser.format_for_storage(parsed)

        self.assertEqual(parsed["meta"]["title"], "测试中标公告")
        self.assertEqual(parsed["meta"]["publish_date"], "2026-03-13")
        self.assertEqual(formatted["buyer_name"], "测试采购单位")
        self.assertEqual(formatted["buyer_contact"], "张三")
        self.assertEqual(formatted["buyer_phone"], "010-88888888")
        self.assertEqual(formatted["agent_name"], "测试代理机构")
        self.assertEqual(formatted["agent_contact"], "李四")
        self.assertEqual(len(formatted["agent_contacts_list"]), 2)
        self.assertEqual(formatted["project_phone"], "010-66666666")
        self.assertEqual(formatted["supplier"], "测试供应商")


if __name__ == "__main__":
    unittest.main()
