// Minimal LTE+EPC+Multicast ns-3 simulation for EMMA
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/lte-module.h"
#include "ns3/epc-helper.h"
#include "ns3/applications-module.h"
#include <fstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("EmmaLteSim");

class MulticastSender : public Application {
public:
  MulticastSender() {}
  void Setup(Address multicast, uint16_t port, std::string filename) {
    m_multicast = multicast;
    m_port = port;
    m_filename = filename;
  }
  virtual void StartApplication() {
    m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
    m_socket->SetAllowBroadcast(true);
    m_socket->Connect(InetSocketAddress(Ipv4Address::ConvertFrom(m_multicast), m_port));
    std::ifstream file(m_filename, std::ios::binary);
    std::vector<char> buffer((std::istreambuf_iterator<char>(file)), {});
    Simulator::Schedule(Seconds(1.0), &MulticastSender::Send, this, buffer, 0);
  }
  void Send(std::vector<char> buffer, size_t offset) {
    size_t chunk = 1024;
    if (offset < buffer.size()) {
      size_t len = std::min(chunk, buffer.size() - offset);
      Ptr<Packet> p = Create<Packet>((uint8_t*)&buffer[offset], len);
      m_socket->Send(p);
      Simulator::Schedule(MilliSeconds(10), &MulticastSender::Send, this, buffer, offset + len);
    }
  }
private:
  Ptr<Socket> m_socket;
  Address m_multicast;
  uint16_t m_port;
  std::string m_filename;
};

int main(int argc, char *argv[]) {
  CommandLine cmd;
  std::string capFile = "alert123.xml";
  cmd.AddValue("capFile", "CAP XML file to send", capFile);
  cmd.Parse(argc, argv);

  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper>();
  Ptr<LteHelper> lteHelper = CreateObject<LteHelper>();
  lteHelper->SetEpcHelper(epcHelper);

  NodeContainer enbNodes, ueNodes;
  enbNodes.Create(1);
  ueNodes.Create(10);

  MobilityHelper mobility;
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(enbNodes);
  mobility.Install(ueNodes);

  NetDeviceContainer enbLteDevs = lteHelper->InstallEnbDevice(enbNodes);
  NetDeviceContainer ueLteDevs = lteHelper->InstallUeDevice(ueNodes);

  InternetStackHelper internet;
  internet.Install(ueNodes);

  Ipv4InterfaceContainer ueIpIfaces = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueLteDevs));
  for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    lteHelper->Attach(ueLteDevs.Get(i), enbLteDevs.Get(0));

  // Multicast sender on eNodeB
  Ipv4Address multicastGroup("239.255.0.1");
  uint16_t port = 5000;
  Ptr<MulticastSender> sender = CreateObject<MulticastSender>();
  sender->Setup(Address(multicastGroup), port, capFile);
  enbNodes.Get(0)->AddApplication(sender);
  sender->SetStartTime(Seconds(0.0));

  // PacketSink on UEs
  for (uint32_t i = 0; i < ueNodes.GetN(); ++i) {
    TypeId tid = TypeId::LookupByName("ns3::UdpSocketFactory");
    Ptr<Socket> sink = Socket::CreateSocket(ueNodes.Get(i), tid);
    InetSocketAddress local = InetSocketAddress(multicastGroup, port);
    sink->Bind(local);
    sink->SetRecvCallback(MakeCallback([](Ptr<Socket> socket) {
      Ptr<Packet> packet;
      Address from;
      while ((packet = socket->RecvFrom(from))) {
        NS_LOG_UNCOND("UE " << socket->GetNode()->GetId() << " received at " << Simulator::Now().GetSeconds());
      }
    }));
  }

  Simulator::Stop(Seconds(5.0));
  Simulator::Run();
  Simulator::Destroy();
  return 0;
} 