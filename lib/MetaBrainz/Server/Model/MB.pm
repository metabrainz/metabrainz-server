package MetaBrainz::Server::Model::MB;
use Moose;

extends 'Catalyst::Model';

use aliased 'MusicBrainz::Server::DatabaseConnectionFactory';
use DBDefs;

use MetaBrainz::Context;

has 'context' => (
    isa        => 'MetaBrainz::Context',
    is         => 'rw',
    lazy_build => 1,
    handles    => [qw( cache dbh )] # XXX Hack - Model::Feeds should be in Data
);

sub _build_context {
    my $self = shift;

    return MetaBrainz::Context->new(
        conn => DatabaseConnectionFactory->get_connection('METABRAINZ'),
        cache_manager => MusicBrainz::Server::CacheManager->new(
            profiles => {
                external => {
                    class => 'Cache::Memcached::Fast',
                    keys => [qw( wikidoc wikidoc-index )],
                    options => {
                        servers => DBDefs::MEMCACHED_SERVERS(),
                        namespace => "metabrainz:"
                    },
                },
                null => {
                    class => 'Cache::Null',
                    wrapped => 1,
                },
            },
            default_profile => 'null',
        ),
        data_prefix => 'MetaBrainz::Data'
    );
}


sub BUILD {
    my ($self) = @_;
    $self->inject(
        FileCache => 'MusicBrainz::Server::Data::FileCache',
        static_dir => '&DBDefs::STATIC_FILES_DIR'
    );
    $self->inject(
        Donation => 'MetaBrainz::Data::Donation'
    );
    $self->inject(
        WikiDoc => 'MusicBrainz::Server::Data::WikiDoc'
    );
    $self->inject(
        WikiDocIndex => 'MusicBrainz::Server::Data::WikiDocIndex'
    );
}

sub inject {
    my ($self, $name, $class, %opts) = @_;
    Class::MOP::load_class($class);

    my $dao = $class->new(c => $self->context, %opts);
    Class::MOP::Class->create(
        "MetaBrainz::Server::Model::$name" =>
            methods => {
                ACCEPT_CONTEXT => sub {
                    return $dao
                }
            });
}

sub expand_modules {
    my $self = shift;
    return
        map { "MetaBrainz::Server::Model::$_" }
            qw( Donation FileCache WikiDoc WikiDocIndex );
}

1;
