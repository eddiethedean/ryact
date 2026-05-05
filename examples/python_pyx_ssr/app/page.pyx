<main className="shell">
  <header key="hero">
    <h1 key="title">Python Ryact via PYX</h1>
    <p key="lead" className="lead">
      This page is authored in
      <code key="c0" className="mono">app/page.pyx</code>
      , compiled to
      <code key="c1" className="mono">h()</code>
      calls, then rendered with ryact-dom. No JS bundle.
    </p>
  </header>
  <section key="sec-pyx" className="card">
    <h2 key="h2a">Build step</h2>
    <p key="pa">
      Run
      <code key="c2" className="mono">python build.py</code>
      for
      <code key="c3" className="mono">ryact-build pyx</code>
      then
      <code key="c4" className="mono">ryact-build static</code>
      .
    </p>
  </section>
  <section key="sec-dev" className="card">
    <h2 key="h2b">Dev</h2>
    <p key="pb">
      Use
      <code key="c5" className="mono">ryact-dev python</code>
      with
      <code key="c6" className="mono">--build</code>
      and
      <code key="c7" className="mono">--run</code>
      . Edits to
      <code key="c8" className="mono">.pyx</code>
      files trigger a rebuild and server restart.
    </p>
  </section>
</main>
