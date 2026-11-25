"""Minimal Maven-less Eclipse Java project files for JDT LS scenarios.

A plain folder of .java files makes JDT LS fall back to its "standalone files" /
invisible-project mode, whose classpath and build timing are less predictable. A
hand-written .project/.classpath pair gives a real JDT project with the Java
builder enabled, which is what the state-inconsistency cases need.
"""

from __future__ import annotations

from typing import Dict

PROJECT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
  <name>{name}</name>
  <comment></comment>
  <projects></projects>
  <buildSpec>
    <buildCommand>
      <name>org.eclipse.jdt.core.javabuilder</name>
      <arguments></arguments>
    </buildCommand>
  </buildSpec>
  <natures>
    <nature>org.eclipse.jdt.core.javanature</nature>
  </natures>
</projectDescription>
"""

CLASSPATH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<classpath>
  <classpathentry kind="src" path="src"/>
  <classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER"/>
  <classpathentry kind="output" path="bin"/>
</classpath>
"""

PREFS = """eclipse.preferences.version=1
org.eclipse.jdt.core.compiler.codegen.targetPlatform=17
org.eclipse.jdt.core.compiler.compliance=17
org.eclipse.jdt.core.compiler.source=17
org.eclipse.jdt.core.compiler.problem.unusedImport=warning
org.eclipse.jdt.core.compiler.problem.unusedLocal=warning
"""


def project_files(name: str = "repro") -> Dict[str, str]:
    """Scaffolding files (no sources) for a compilable JDT project."""
    return {
        ".project": PROJECT_XML.format(name=name),
        ".classpath": CLASSPATH_XML,
        ".settings/org.eclipse.jdt.core.prefs": PREFS,
    }


def with_sources(sources: Dict[str, str], name: str = "repro") -> Dict[str, str]:
    """Combine `src/...` sources with the project scaffolding."""
    files = project_files(name)
    files.update(sources)
    return files


__all__ = ["CLASSPATH_XML", "PREFS", "PROJECT_XML", "project_files", "with_sources"]
