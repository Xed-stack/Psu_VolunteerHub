from tests.html_helpers import parse_html, form_with_control, form_values


def test_semantic_queries_tolerate_attributes_whitespace_and_repeated_controls():
    document = parse_html('''
      <form><input name="campus" value="unrelated"><input name="award_year" value="2025"></form>
      <form class="filters"><input value="1" type="hidden" name="campus" />
        <input name="campus" value="2" type="hidden">
        <input name="unchecked" value="no" type="checkbox">
        <select name="award_year"><option value="2025">2025</option>
          <option selected value="2026"> 2026 </option></select>
      </form>
      <div aria-label="Recent registrations"><table><tbody><tr>
        <td data-label="Activity"> Synthetic &amp; activity </td>
        <td class="cell" data-label="Certificate"> <span>Eligible</span> </td>
      </tr></tbody></table></div>
    ''')
    assert form_values(form_with_control(document, 'award_year', tags=('select',))) == {
        'campus': ['1', '2'], 'award_year': ['2026']}
    region = document.one('div', **{'aria-label': 'Recent registrations'})
    assert [cell.text for cell in region.all('td')] == ['Synthetic & activity', 'Eligible']
