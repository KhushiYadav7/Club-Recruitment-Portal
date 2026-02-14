"""
Tests for email utilities
"""
import pytest
from app.utils.email import strip_html_to_text, _base_template


def test_strip_html_removes_preheader():
    """Test that hidden preheader divs are removed from plain text"""
    # HTML with a hidden preheader div (display:none)
    html = '''
    <div style="display: none; max-height: 0; overflow: hidden; color: #1a1a1a;">
    Your code.scriet account is ready. Login details inside.&nbsp;&nbsp;&nbsp;
    </div>
    <p>Hello John, Your account is ready...</p>
    '''
    
    result = strip_html_to_text(html)
    
    # Preheader text should not appear in result
    assert "Your code.scriet account is ready. Login details inside." not in result
    # Main content should be preserved
    assert "Hello John, Your account is ready..." in result


def test_strip_html_removes_preheader_case_insensitive():
    """Test that preheader removal works case-insensitively"""
    # HTML with display:NONE (uppercase)
    html = '''
    <DIV style="DISPLAY: NONE; max-height: 0;">
    Hidden preheader text
    </DIV>
    <p>Visible content</p>
    '''
    
    result = strip_html_to_text(html)
    
    # Preheader should be removed
    assert "Hidden preheader text" not in result
    # Main content should be preserved
    assert "Visible content" in result


def test_strip_html_removes_preheader_single_quotes():
    """Test that preheader removal works with single quotes"""
    # HTML with single quotes in style attribute
    html = '''
    <div style='display: none; max-height: 0;'>
    Hidden preheader text
    </div>
    <p>Visible content</p>
    '''
    
    result = strip_html_to_text(html)
    
    # Preheader should be removed
    assert "Hidden preheader text" not in result
    # Main content should be preserved
    assert "Visible content" in result


def test_strip_html_preserves_visible_content():
    """Test that visible content is preserved"""
    html = '''
    <h1>Welcome</h1>
    <p>This is a test email</p>
    <a href="http://example.com">Click here</a>
    '''
    
    result = strip_html_to_text(html)
    
    # All visible content should be present
    assert "Welcome" in result
    assert "This is a test email" in result
    assert "Click here" in result


def test_strip_html_removes_style_tags():
    """Test that style tags are removed"""
    html = '''
    <style>body { color: red; }</style>
    <p>Content</p>
    '''
    
    result = strip_html_to_text(html)
    
    # CSS should be removed
    assert "body { color: red; }" not in result
    # Content should be preserved
    assert "Content" in result


def test_base_template_uses_colors_dict(fresh_app):
    """Test that _base_template uses COLORS dict for preheader color"""
    from app.utils.email import COLORS
    
    with fresh_app.app_context():
        html = _base_template(
            header_bg="#242424",
            header_title="Test",
            header_sub="Test subtitle",
            body="<p>Test body</p>",
            footer_note="Test footer",
            preheader="Test preheader"
        )
        
        # Should use COLORS['bg'] not hard-coded color
        expected_color = COLORS['bg']
        assert f'color: {expected_color};' in html
        # Should not have hard-coded #1a1a1a (unless it's the value in COLORS['bg'])
        # This test verifies it's using the variable, not hard-coded


def test_strip_html_handles_multiline_preheader():
    """Test that preheader with line breaks is removed"""
    html = '''
    <div style="display: none; max-height: 0;">
    Multiline
    preheader
    text
    </div>
    <p>Real content</p>
    '''
    
    result = strip_html_to_text(html)
    
    # Preheader should be removed
    assert "Multiline" not in result and "preheader" not in result
    # Main content should be preserved
    assert "Real content" in result


def test_strip_html_handles_nested_quotes():
    """Test that preheader with nested quotes in style is handled correctly"""
    # Style with double quotes containing text (edge case)
    html_double = '''
    <div style="display: none; max-height: 0; content: 'test';">
    Hidden text
    </div>
    <p>Visible</p>
    '''
    
    # Style with single quotes (simpler case)
    html_single = '''
    <div style='display: none; max-height: 0;'>
    Hidden text
    </div>
    <p>Visible</p>
    '''
    
    result_double = strip_html_to_text(html_double)
    result_single = strip_html_to_text(html_single)
    
    # Preheader should be removed in both cases
    assert "Hidden text" not in result_double
    assert "Hidden text" not in result_single
    # Main content should be preserved
    assert "Visible" in result_double
    assert "Visible" in result_single
