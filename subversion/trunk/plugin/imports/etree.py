try:
    # lxml
    from lxml import etree
    from lxml.etree import XMLSyntaxError
    HAVE_LXML = True
    LIBRARY=("lxml " + etree.__version__ + 
        " (libxml " + '.'.join(str(i) for i in etree.LIBXML_VERSION) + ")")
except ImportError:
    HAVE_LXML = False
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        from exceptions import SyntaxError as XMLSyntaxError
        LIBRARY="cElementTree"
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            from xml.parsers.expat import ExpatError as XMLSyntaxError
            LIBRARY="ElementTree"
        except ImportError:
            etree = None

def check():
    """
    Check wether any implementation of ElementTree library is installed, or not
    
    @raise AssertionError: if ElementTree is not installed
    """
    
    assert etree is not None, "No implementation of ElementTree library installed"
    
    if not HAVE_LXML:
        print "WARNING: lxml library is not installed. Data format validation will not be used"

def version():
    """
    Check pygtk libraries versions
    
    @return: versions of each library connected to PyGTK
    @rtype: list of (str, str)
    """
    return [
        (_("etree version"), LIBRARY),
    ]
