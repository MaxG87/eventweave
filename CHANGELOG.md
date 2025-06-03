# Changelog

## [0.4.0](https://github.com/MaxG87/eventweave/compare/v0.3.0...v0.4.0) (2025-06-03)


### Features

* Add correct handling of first scenario with atomic events ([144a02e](https://github.com/MaxG87/eventweave/commit/144a02e9197b709cd2d91e305881f600f36dbf46))
* Correctly handle atomic events ([3dd0dae](https://github.com/MaxG87/eventweave/commit/3dd0dae8db52473edd0c18d21f54ca1a160687ef))
* Handle atomic event in middle of the stream ([4421ce8](https://github.com/MaxG87/eventweave/commit/4421ce89265deb3f639a2d3b993213ca8a60cd6b))
* Handle atomic event with back-to-back scenario ([2f6a4ea](https://github.com/MaxG87/eventweave/commit/2f6a4eae0393c2712eac2c075831e5e49d1069c8))
* Handle atomic events at the end of the stream ([1abb7a7](https://github.com/MaxG87/eventweave/commit/1abb7a77dd42fa3a2f4ca855872ce26c0b3a3b34))
* Handle atomic events at the start of the stream ([2a7f208](https://github.com/MaxG87/eventweave/commit/2a7f20854cf5f6d97ebf0d67a7cacc0850bb89ff))
* Handle atomic events back-to-back with the first normal event ([80b2d7f](https://github.com/MaxG87/eventweave/commit/80b2d7f45400f1d3b0aae03eafcd2041cb862823))
* Handle atomic events back-to-back with the last normal event ([aa657c3](https://github.com/MaxG87/eventweave/commit/aa657c3e2b4e6eebe37a856f2d68f8c697aed6ef))
* Handle special case of only atomic events ([54739dc](https://github.com/MaxG87/eventweave/commit/54739dc68b804215a8c9835fe03e6e611f6ec639))


### Bug Fixes

* Correctly handle back-to-back events ([6e989ce](https://github.com/MaxG87/eventweave/commit/6e989ce2cf9fd82b4c800e727d67844d252f71b4))
* Handle back-to-back events correctly ([87b8b19](https://github.com/MaxG87/eventweave/commit/87b8b19f6ed99abec824b2daf0330c24c13a6f61))


### Dependencies

* Relock dependencies ([bfea356](https://github.com/MaxG87/eventweave/commit/bfea356ff6fd83b3d5a0acefdad2239e22df3f8a))


### Documentation

* Update documentation regarding atomic events ([a0d5540](https://github.com/MaxG87/eventweave/commit/a0d5540af0fdf0c421c830dac6a062195b1ac89b))

## [0.3.0](https://github.com/MaxG87/eventweave/compare/v0.2.0...v0.3.0) (2025-05-29)


### Continuous Integration

* Fix automated publishing to PyPI ([252e942](https://github.com/MaxG87/eventweave/commit/252e942b4f8a91bc075378d407e070c59956a7cd))

## [0.2.0](https://github.com/MaxG87/eventweave/compare/v0.1.0...v0.2.0) (2025-05-23)


### Features

* Lower minimum Python version to 3.10 ([313b20b](https://github.com/MaxG87/eventweave/commit/313b20b565c61f247c7f36280da34e4c8ad55d50))
* Return frozensets of events ([7db4d96](https://github.com/MaxG87/eventweave/commit/7db4d96fd52fc9b3cfa5e514dc78f896f609c3c5))


### Documentation

* Add example usage to docstring ([792aa3a](https://github.com/MaxG87/eventweave/commit/792aa3a313090aec55db63f105f367ec5cb782ce))
* Add project README ([b7647ee](https://github.com/MaxG87/eventweave/commit/b7647eedacec69cec824008acd2f21b597212c10))
* Include README to PyPI description ([65aee2b](https://github.com/MaxG87/eventweave/commit/65aee2bfb7c0a99812e62ddf8f30b488df5fa3b6))
* Mention two edge cases not yet supported ([8cc1daa](https://github.com/MaxG87/eventweave/commit/8cc1daa348443e0a8f6b6e876122f33cba5961dc))
* Test that code examples in README are correct ([58073c3](https://github.com/MaxG87/eventweave/commit/58073c311f7c94a0b46f0c8a87908b45ab6a2e93))

## 0.1.0 (2025-05-22)


### Features

* Adapt initial tests to new constraints ([1c3d8be](https://github.com/MaxG87/eventweave/commit/1c3d8be1413047f5036dad2b408230c9c944d2f4))
* Add first acceptable function signature ([ae5ff91](https://github.com/MaxG87/eventweave/commit/ae5ff91e9fc9097c2efe8f8b8ff49e8ef24eda24))
* Add implementation of interweave ([a963af3](https://github.com/MaxG87/eventweave/commit/a963af3a54834f5b106c6d80863549e193faff46))
* Handle boundary conditions better ([3d6558b](https://github.com/MaxG87/eventweave/commit/3d6558be72b61c07d203750c2b5644dc0d189ec1))
* Implement first simple special case ([3b874c0](https://github.com/MaxG87/eventweave/commit/3b874c0a4b0c6d2554d9a9bf5ff4f42e5dc61b97))
* Reject invalid events ([443e2a1](https://github.com/MaxG87/eventweave/commit/443e2a1fa54f6aa4aa289956c63eef80851928ca))


### Dependencies

* **dev:** Add all dev-dependencies ([b94df9e](https://github.com/MaxG87/eventweave/commit/b94df9eb3c1f7a77c3139300ce5dc1a419fb8fdf))


### Documentation

* Extend docstring ([7182f32](https://github.com/MaxG87/eventweave/commit/7182f325adea5f2df40a434d9f008a95305487d6))
* Extend project description a bit ([2d83d18](https://github.com/MaxG87/eventweave/commit/2d83d182fee8abe4fd0bdb08d722c3b32eed4877))
